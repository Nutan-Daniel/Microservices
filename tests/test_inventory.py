"""Inventory service tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from inventory.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt
    token = jwt.encode({"sub": "user-1"}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_reserve_stock(client, auth_headers):
    resp = client.post(
        "/inventory/reserve",
        json={"product_id": "prod-1", "quantity": 5, "order_id": "order-1"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "reserved"
    assert data["quantity"] == 5
    assert data["order_id"] == "order-1"


def test_reserve_negative_quantity(client, auth_headers):
    resp = client.post(
        "/inventory/reserve",
        json={"product_id": "prod-1", "quantity": 0, "order_id": "order-1"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_release_stock(client, auth_headers):
    # Reserve first
    resp = client.post(
        "/inventory/reserve",
        json={"product_id": "prod-2", "quantity": 3, "order_id": "order-2"},
        headers=auth_headers,
    )
    reservation_id = resp.json()["id"]

    # Release
    resp = client.post(
        "/inventory/release",
        json={"reservation_id": reservation_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "released"


def test_release_nonexistent(client, auth_headers):
    resp = client.post(
        "/inventory/release",
        json={"reservation_id": "does-not-exist"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_check_stock(client, auth_headers):
    resp = client.get("/inventory/stock/prod-3", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "available_quantity" in data


def test_get_reservations_for_order(client, auth_headers):
    # Reserve for an order
    client.post(
        "/inventory/reserve",
        json={"product_id": "prod-4", "quantity": 2, "order_id": "order-4"},
        headers=auth_headers,
    )

    resp = client.get("/inventory/reservations/order-4", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["order_id"] == "order-4"
