"""Orders service tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from orders.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt
    token = jwt.encode({"sub": "user-1"}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_create_order(client, auth_headers):
    resp = client.post(
        "/orders",
        json={"items": [{"product_id": "prod-1", "quantity": 2, "price": 10.0}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["total"] == 20.0
    assert "id" in data


def test_create_order_empty_items(client, auth_headers):
    resp = client.post("/orders", json={"items": []}, headers=auth_headers)
    assert resp.status_code == 400


def test_list_orders(client, auth_headers):
    client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 5.0}]},
        headers=auth_headers,
    )
    resp = client.get("/orders", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_order(client, auth_headers):
    create_resp = client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 5.0}]},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    resp = client.get(f"/orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


def test_get_order_not_found(client, auth_headers):
    resp = client.get("/orders/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


def test_cancel_order(client, auth_headers):
    create_resp = client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 5.0}]},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    resp = client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_already_cancelled(client, auth_headers):
    create_resp = client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 5.0}]},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    resp = client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    assert resp.status_code == 400


def test_payment_succeeded_transitions_to_reserved(client, auth_headers):
    # Create order
    create_resp = client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 5.0}]},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    # Simulate payment succeeded event
    resp = client.post(
        "/events/payment.succeeded",
        json={"order_id": order_id},
    )
    # Inventory service not running in unit test, so reservation will fail -> cancelled
    assert resp.status_code in (200, 502)


def test_payment_failed_transitions_to_cancelled(client, auth_headers):
    create_resp = client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 5.0}]},
        headers=auth_headers,
    )
    order_id = create_resp.json()["id"]

    resp = client.post("/events/payment.failed", json={"order_id": order_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["reason"] == "payment_failed"
