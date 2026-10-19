"""Inventory service - stock reservations, decrements, releases, livestock tracking."""

import os
import uuid
from datetime import datetime, timezone

import jwt
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from shared.outbox import OutboxRelay
from shared.publisher import StreamPublisher

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    id = Column(String, primary_key=True, index=True)
    product_id = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # reserved / released / decremented / doa_reported
    order_id = Column(String, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    is_livestock = Column(Integer, nullable=False, default=0)  # 0/1 boolean
    doa_reported = Column(Integer, nullable=False, default=0)  # 0/1 boolean
    doa_reported_at = Column(DateTime, nullable=True)
    doa_evidence_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(String, primary_key=True, index=True)
    aggregate_type = Column(String, nullable=False)
    aggregate_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):  # noqa: B008
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Redis + outbox relay
# ---------------------------------------------------------------------------
_redis_client = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class StockReserveRequest(BaseModel):
    product_id: str
    quantity: int
    order_id: str
    is_livestock: bool = False


class StockReleaseRequest(BaseModel):
    reservation_id: str


class StockCheckResponse(BaseModel):
    product_id: str
    available_quantity: int


class StockReservationResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    status: str
    order_id: str | None
    is_livestock: bool
    doa_reported: bool
    created_at: datetime


class DOAReportRequest(BaseModel):
    reservation_id: str
    evidence_url: str | None = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="inventory-service")


async def _publish_event(db, event_type: str, aggregate_type: str, aggregate_id: str,
                         idempotency_key: str, payload: dict):
    """Publish event via outbox relay; non-fatal if Redis is down."""
    try:
        r = _redis_client
        if r is None:
            r = await get_redis()
        publisher = StreamPublisher(r)
        relay = OutboxRelay(db, publisher)
        await relay.publish(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=idempotency_key,
            payload=payload,
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


@app.post("/inventory/reserve", response_model=StockReservationResponse, status_code=201)
async def reserve_stock(req: StockReserveRequest, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    reservation_id = str(uuid.uuid4())
    reservation = StockReservation(
        id=reservation_id,
        product_id=req.product_id,
        quantity=req.quantity,
        status="reserved",
        order_id=req.order_id,
        reason="reserved_for_order",
        is_livestock=1 if req.is_livestock else 0,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    await _publish_event(
        db,
        event_type="stock.reserved",
        aggregate_type="inventory",
        aggregate_id=reservation_id,
        idempotency_key=reservation_id,
        payload={"reservation_id": reservation_id, "product_id": req.product_id,
                 "quantity": req.quantity, "order_id": req.order_id, "is_livestock": req.is_livestock},
    )

    return StockReservationResponse(
        id=reservation.id,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=reservation.status,
        order_id=reservation.order_id,
        is_livestock=bool(reservation.is_livestock),
        doa_reported=bool(reservation.doa_reported),
        created_at=reservation.created_at,
    )


@app.post("/inventory/release", response_model=StockReservationResponse)
async def release_stock(req: StockReleaseRequest, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    reservation = db.query(StockReservation).filter(StockReservation.id == req.reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status != "reserved":
        raise HTTPException(status_code=400, detail=f"Cannot release stock in status '{reservation.status}'")

    reservation.status = "released"
    reservation.reason = "released_for_order_cancellation"
    db.commit()
    db.refresh(reservation)

    rid = reservation.id
    await _publish_event(
        db,
        event_type="stock.released",
        aggregate_type="inventory",
        aggregate_id=rid,
        idempotency_key=f"release-{rid}",
        payload={"reservation_id": reservation.id, "product_id": reservation.product_id,
                 "quantity": reservation.quantity, "order_id": reservation.order_id},
    )

    return StockReservationResponse(
        id=reservation.id,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=reservation.status,
        order_id=reservation.order_id,
        is_livestock=bool(reservation.is_livestock),
        doa_reported=bool(reservation.doa_reported),
        created_at=reservation.created_at,
    )


@app.post("/inventory/reservations/{reservation_id}/doa", response_model=StockReservationResponse)
async def report_doa(reservation_id: str, req: DOAReportRequest, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    reservation = db.query(StockReservation).filter(StockReservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if not reservation.is_livestock:
        raise HTTPException(status_code=400, detail="DOA claims only apply to livestock")
    if reservation.doa_reported:
        raise HTTPException(status_code=400, detail="DOA already reported for this reservation")

    reservation.status = "doa_reported"
    reservation.doa_reported = 1
    reservation.doa_reported_at = datetime.now(timezone.utc)
    reservation.doa_evidence_url = req.evidence_url
    reservation.reason = "dead_on_arrival"
    db.commit()
    db.refresh(reservation)

    await _publish_event(
        db,
        event_type="stock.doa_reported",
        aggregate_type="inventory",
        aggregate_id=reservation_id,
        idempotency_key=f"doa-{reservation_id}",
        payload={"reservation_id": reservation.id, "product_id": reservation.product_id,
                 "quantity": reservation.quantity, "order_id": reservation.order_id,
                 "evidence_url": req.evidence_url},
    )

    return StockReservationResponse(
        id=reservation.id,
        product_id=reservation.product_id,
        quantity=reservation.quantity,
        status=reservation.status,
        order_id=reservation.order_id,
        is_livestock=bool(reservation.is_livestock),
        doa_reported=bool(reservation.doa_reported),
        created_at=reservation.created_at,
    )


@app.get("/inventory/stock/{product_id}", response_model=StockCheckResponse)
async def check_stock(product_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    reserved = db.query(StockReservation).filter(
        StockReservation.product_id == product_id,
        StockReservation.status == "reserved",
    ).all()
    reserved_qty = sum(r.quantity for r in reserved)

    # Snapshot quantity from catalog if available; default 0 here (catalog owns stock snapshot)
    available_qty = 0 - reserved_qty

    return StockCheckResponse(product_id=product_id, available_quantity=available_qty)


@app.get("/inventory/reservations/{order_id}", response_model=list[StockReservationResponse])
async def get_reservations_for_order(order_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    reservations = db.query(StockReservation).filter(StockReservation.order_id == order_id).all()
    return [
        StockReservationResponse(
            id=r.id,
            product_id=r.product_id,
            quantity=r.quantity,
            status=r.status,
            order_id=r.order_id,
            is_livestock=bool(r.is_livestock),
            doa_reported=bool(r.doa_reported),
            created_at=r.created_at,
        )
        for r in reservations
    ]