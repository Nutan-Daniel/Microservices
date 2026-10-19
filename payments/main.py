"""Payments service - Stripe sandbox integration, webhook verification, idempotent callbacks."""

import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone

import jwt
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Numeric, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from shared.outbox import OutboxRelay
from shared.publisher import StreamPublisher

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./payments.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "sandbox")  # sandbox only
PAYMENT_PROVIDER_URL = os.getenv("PAYMENT_PROVIDER_URL", "http://localhost:9000")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "whsec_dev-change-me-32-bytes-minimum")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, nullable=False)  # succeeded / failed / refunded
    provider_reference = Column(String, nullable=True, index=True)
    idempotency_key = Column(String, nullable=False, unique=True, index=True)
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
class ChargeRequest(BaseModel):
    order_id: str
    amount: float


class RefundRequest(BaseModel):
    payment_id: str


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    amount: float
    status: str
    provider_reference: str | None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="payments-service")


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


# ---------------------------------------------------------------------------
# Charge endpoint (sandbox provider)
# ---------------------------------------------------------------------------
@app.post("/payments/charge", response_model=PaymentResponse, status_code=201)
async def charge(charge_in: ChargeRequest, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    idempotency_key = f"charge-{charge_in.order_id}"

    # Idempotency: same payment intent processed once
    existing = db.query(PaymentTransaction).filter(
        PaymentTransaction.idempotency_key == idempotency_key
    ).first()
    if existing:
        return JSONResponse(
            status_code=200,
            content={
                "id": existing.id,
                "order_id": existing.order_id,
                "amount": float(existing.amount),
                "status": existing.status,
                "provider_reference": existing.provider_reference,
            },
        )

    # Sandbox provider charge (no real card data; store only provider reference)
    provider_reference = f"sandbox_{uuid.uuid4()}"
    tx = PaymentTransaction(
        id=str(uuid.uuid4()),
        order_id=charge_in.order_id,
        amount=charge_in.amount,
        status="succeeded",
        provider_reference=provider_reference,
        idempotency_key=idempotency_key,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    await _publish_event(
        db,
        event_type="payment.succeeded",
        aggregate_type="payment",
        aggregate_id=tx.id,
        idempotency_key=f"payment-succeeded-{tx.id}",
        payload={"payment_id": tx.id, "order_id": charge_in.order_id,
                 "amount": str(charge_in.amount), "provider_reference": provider_reference},
    )

    return PaymentResponse(
        id=tx.id,
        order_id=tx.order_id,
        amount=float(tx.amount),
        status=tx.status,
        provider_reference=tx.provider_reference,
    )


@app.post("/payments/refund", response_model=PaymentResponse)
async def refund(refund_in: RefundRequest, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    tx = db.query(PaymentTransaction).filter(PaymentTransaction.id == refund_in.payment_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Payment not found")
    if tx.status != "succeeded":
        raise HTTPException(status_code=400, detail=f"Cannot refund payment in status '{tx.status}'")

    tx.status = "refunded"
    tx.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tx)

    await _publish_event(
        db,
        event_type="payment.refunded",
        aggregate_type="payment",
        aggregate_id=tx.id,
        idempotency_key=f"refund-{tx.id}",
        payload={"payment_id": tx.id, "order_id": tx.order_id, "amount": str(tx.amount)},
    )

    return PaymentResponse(
        id=tx.id,
        order_id=tx.order_id,
        amount=float(tx.amount),
        status=tx.status,
        provider_reference=tx.provider_reference,
    )


# ---------------------------------------------------------------------------
# Webhook endpoint (Stripe-style signature verification)
# ---------------------------------------------------------------------------
@app.post("/payments/webhook")
async def webhook(request: Request, db=Depends(get_db)):  # noqa: B008
    """Verify provider webhook signature; handle duplicate callbacks idempotently."""
    body = await request.body()
    signature = request.headers.get("stripe-signature", "")

    # Verify webhook signature (sandbox: simple HMAC check; production: Stripe library)
    expected = hmac_sha256_hex(WEBHOOK_SECRET, body)
    if signature != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "payment_intent.succeeded":
        order_id = data.get("order_id") or data.get("metadata", {}).get("order_id")
        amount = float(data.get("amount", 0))
        payment_id = data.get("id")

        if not order_id:
            raise HTTPException(status_code=400, detail="Missing order_id in webhook")

        # Idempotency: same payment intent processed once
        existing = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.provider_reference == payment_id,
        ).first()
        if existing:
            return {"status": "skipped", "reason": "duplicate_webhook"}

        tx = PaymentTransaction(
            id=str(uuid.uuid4()),
            order_id=order_id,
            amount=amount,
            status="succeeded",
            provider_reference=payment_id,
            idempotency_key=f"webhook-{payment_id}",
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        await _publish_event(
            db,
            event_type="payment.succeeded",
            aggregate_type="payment",
            aggregate_id=tx.id,
            idempotency_key=f"payment-succeeded-{tx.id}",
            payload={"payment_id": tx.id, "order_id": order_id,
                     "amount": str(amount), "provider_reference": payment_id},
        )
        return {"status": "processed"}

    elif event_type == "payment_intent.payment_failed":
        order_id = data.get("order_id") or data.get("metadata", {}).get("order_id")
        amount = float(data.get("amount", 0))
        payment_id = data.get("id")

        if not order_id:
            raise HTTPException(status_code=400, detail="Missing order_id in webhook")

        existing = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.provider_reference == payment_id,
        ).first()
        if existing:
            return {"status": "skipped", "reason": "duplicate_webhook"}

        tx = PaymentTransaction(
            id=str(uuid.uuid4()),
            order_id=order_id,
            amount=amount,
            status="failed",
            provider_reference=payment_id,
            idempotency_key=f"webhook-{payment_id}",
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        await _publish_event(
            db,
            event_type="payment.failed",
            aggregate_type="payment",
            aggregate_id=tx.id,
            idempotency_key=f"payment-failed-{tx.id}",
            payload={"payment_id": tx.id, "order_id": order_id,
                     "amount": str(amount), "provider_reference": payment_id},
        )
        return {"status": "processed"}

    return {"status": "ignored", "event_type": event_type}


# ---------------------------------------------------------------------------
# Query endpoints
# ---------------------------------------------------------------------------
@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    tx = db.query(PaymentTransaction).filter(PaymentTransaction.id == payment_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(
        id=tx.id,
        order_id=tx.order_id,
        amount=float(tx.amount),
        status=tx.status,
        provider_reference=tx.provider_reference,
    )


@app.get("/payments/order/{order_id}", response_model=list[PaymentResponse])
async def get_payments_for_order(order_id: str, db=Depends(get_db), current_user: str = Depends(get_current_user)):  # noqa: B008
    txs = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == order_id).all()
    return [
        PaymentResponse(
            id=t.id,
            order_id=t.order_id,
            amount=float(t.amount),
            status=t.status,
            provider_reference=t.provider_reference,
        )
        for t in txs
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def hmac_sha256_hex(secret: str, data: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()