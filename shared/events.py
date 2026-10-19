"""Pydantic event schemas for Redis Streams."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    aggregate_type: str
    aggregate_id: str
    idempotency_key: str
    payload: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str | None = None
    causation_id: str | None = None


# Order events
class OrderCreated(BaseModel):
    order_id: str
    user_id: str
    items: list[dict[str, Any]]
    total: float


class OrderPaid(BaseModel):
    order_id: str
    payment_id: str


class OrderCancelled(BaseModel):
    order_id: str
    reason: str


# Payment events
class PaymentSucceeded(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    provider_reference: str


class PaymentFailed(BaseModel):
    payment_id: str
    order_id: str
    reason: str


# Inventory events
class StockReserved(BaseModel):
    reservation_id: str
    order_id: str
    product_id: str
    quantity: int


class StockReleased(BaseModel):
    reservation_id: str
    order_id: str
    product_id: str
    quantity: int


# User events
class UserCreated(BaseModel):
    user_id: str
    email: str


class UserUpdated(BaseModel):
    user_id: str
    email: str