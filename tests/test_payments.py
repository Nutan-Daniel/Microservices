"""Payments service tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from payments.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt
    token = jwt.encode({"sub": "user-1"}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _unique_order(prefix="order"):
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_charge(client, auth_headers):
    resp = client.post(
        "/payments/charge",
        json={"order_id": _unique_order(), "amount": 99.99},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["amount"] == 99.99
    assert data["provider_reference"] is not None


def test_charge_idempotent(client, auth_headers):
    order_id = _unique_order("idempotent")
    # First charge
    resp1 = client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 50.0},
        headers=auth_headers,
    )
    assert resp1.status_code == 201

    # Same order again - should return existing transaction with 200
    resp2 = client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 50.0},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["id"] == resp1.json()["id"]


def test_refund(client, auth_headers):
    charge_resp = client.post(
        "/payments/charge",
        json={"order_id": _unique_order("refund"), "amount": 30.0},
        headers=auth_headers,
    )
    assert charge_resp.status_code == 201
    payment_id = charge_resp.json()["id"]

    resp = client.post("/payments/refund", json={"payment_id": payment_id}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"


def test_refund_already_refunded(client, auth_headers):
    charge_resp = client.post(
        "/payments/charge",
        json={"order_id": _unique_order("refund2"), "amount": 30.0},
        headers=auth_headers,
    )
    payment_id = charge_resp.json()["id"]

    client.post("/payments/refund", json={"payment_id": payment_id}, headers=auth_headers)
    resp = client.post("/payments/refund", json={"payment_id": payment_id}, headers=auth_headers)
    assert resp.status_code == 400


def test_get_payment(client, auth_headers):
    charge_resp = client.post(
        "/payments/charge",
        json={"order_id": _unique_order("get"), "amount": 15.0},
        headers=auth_headers,
    )
    payment_id = charge_resp.json()["id"]

    resp = client.get(f"/payments/{payment_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == payment_id


def test_get_payments_for_order(client, auth_headers):
    order_id = _unique_order("multi")
    client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 10.0},
        headers=auth_headers,
    )
    # Same order_id charged again is idempotent - returns same transaction
    client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 20.0},
        headers=auth_headers,
    )

    resp = client.get(f"/payments/order/{order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1  # idempotent: same order_id = one transaction


def test_webhook_succeeded(client):
    import hashlib
    import hmac
    import json
    import uuid

    order_id = _unique_order("webhook")
    payload = json.dumps({
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": f"pi-{uuid.uuid4().hex[:8]}", "order_id": order_id, "amount": 42.0}},
    }).encode()
    signature = hmac.new(os.environ["WEBHOOK_SECRET"].encode(), payload, hashlib.sha256).hexdigest()

    resp = client.post(
        "/payments/webhook",
        content=payload,
        headers={"stripe-signature": signature},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"


def test_webhook_duplicate(client):
    import hashlib
    import hmac
    import json
    import uuid

    order_id = _unique_order("dup")
    pi_id = f"pi-{uuid.uuid4().hex[:8]}"
    payload = json.dumps({
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": pi_id, "order_id": order_id, "amount": 7.0}},
    }).encode()
    signature = hmac.new(os.environ["WEBHOOK_SECRET"].encode(), payload, hashlib.sha256).hexdigest()

    # First webhook
    resp1 = client.post(
        "/payments/webhook",
        content=payload,
        headers={"stripe-signature": signature},
    )
    assert resp1.status_code == 200

    # Duplicate webhook - should be skipped
    resp2 = client.post(
        "/payments/webhook",
        content=payload,
        headers={"stripe-signature": signature},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "skipped"
    assert resp2.json()["reason"] == "duplicate_webhook"


def test_webhook_invalid_signature(client):
    resp = client.post(
        "/payments/webhook",
        content=b'{"type":"test"}',
        headers={"stripe-signature": "bad-signature"},
    )
    assert resp.status_code == 401
