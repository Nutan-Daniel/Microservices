"""Orders service - order state machine, saga coordination, compensating transactions."""

import os
import uuid
from datetime import datetime, timezone

import httpx
import jwt
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from shared.outbox import OutboxRelay
from shared.publisher import StreamPublisher

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orders.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://localhost:8005")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:8003")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="pending")  # pending/reserved/confirmed/cancelled
    total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)


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
class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int
    price: float


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]


class OrderResponse(BaseModel):
    id: str
    user_id: str
    status: str
    total: float
    created_at: datetime


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    price: float


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="orders-service")


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


def _transition_order(db, order_id: str, new_status: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    order.status = new_status
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(order_in: OrderCreate, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    if not order_in.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    total = sum(item.quantity * item.price for item in order_in.items)
    order_id = str(uuid.uuid4())
    order = Order(id=order_id, user_id=current_user, status="pending", total=total)
    db.add(order)
    for item in order_in.items:
        order_item = OrderItem(
            id=str(uuid.uuid4()),
            order_id=order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price,
        )
        db.add(order_item)
    db.commit()
    db.refresh(order)

    # Publish order.created -> payments service will consume
    await _publish_event(
        db,
        event_type="order.created",
        aggregate_type="order",
        aggregate_id=order_id,
        idempotency_key=order_id,
        payload={"order_id": order_id, "user_id": current_user, "total": str(total)},
    )

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total=float(order.total),
        created_at=order.created_at,
    )


@app.get("/orders", response_model=list[OrderResponse])
async def list_orders(db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    orders = db.query(Order).filter(Order.user_id == current_user).all()
    return [
        OrderResponse(id=o.id, user_id=o.user_id, status=o.status, total=float(o.total), created_at=o.created_at)
        for o in orders
    ]


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total=float(order.total),
        created_at=order.created_at,
    )


@app.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    if order.status in ("confirmed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in status '{order.status}'")

    order.status = "cancelled"
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    await _publish_event(
        db,
        event_type="order.cancelled",
        aggregate_type="order",
        aggregate_id=order_id,
        idempotency_key=f"cancel-{order_id}",
        payload={"order_id": order_id, "user_id": current_user},
    )

    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total=float(order.total),
        created_at=order.created_at,
    )


# ---------------------------------------------------------------------------
# Async event handlers (consumed by orders service)
# ---------------------------------------------------------------------------
@app.post("/events/payment.succeeded")
async def handle_payment_succeeded(payload: dict, db=Depends(get_db)):  # noqa: B008
    order_id = payload.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order_id")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending":
        # Idempotent: already processed
        return {"status": "skipped", "reason": f"order already {order.status}"}

    # Step 1: Reserve inventory
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{INVENTORY_URL}/inventory/reserve",
                json={"product_id": "", "quantity": 1, "order_id": order_id},
            )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Inventory service unavailable")

    if resp.status_code != 201:
        # Reservation failed -> compensate: cancel order
        _transition_order(db, order_id, "cancelled")
        await _publish_event(
            db,
            event_type="order.cancelled",
            aggregate_type="order",
            aggregate_id=order_id,
            idempotency_key=f"cancel-{order_id}",
            payload={"order_id": order_id, "user_id": order.user_id, "reason": "inventory_reservation_failed"},
        )
        return {"status": "cancelled", "reason": "inventory_reservation_failed"}

        # Step 2: Reservation succeeded -> transition to reserved
        _transition_order(db, order_id, "reserved")
        await _publish_event(
        db,
        event_type="stock.reserved",
        aggregate_type="order",
        aggregate_id=order_id,
        idempotency_key=f"stock-reserved-{order_id}",
        payload={"order_id": order_id, "user_id": order.user_id},
    )

    return {"status": "reserved"}


@app.post("/events/payment.failed")
async def handle_payment_failed(payload: dict, db=Depends(get_db)):  # noqa: B008
    order_id = payload.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order_id")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending":
        return {"status": "skipped", "reason": f"order already {order.status}"}

    # Payment failed -> cancel order (no inventory was reserved yet)
    order.status = "cancelled"
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    await _publish_event(
        db,
        event_type="order.cancelled",
        aggregate_type="order",
        aggregate_id=order_id,
        idempotency_key=f"cancel-{order_id}",
        payload={"order_id": order_id, "user_id": order.user_id, "reason": "payment_failed"},
    )

    return {"status": "cancelled", "reason": "payment_failed"}