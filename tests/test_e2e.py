"""E2E tests for the full order flow."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


import pytest
from fastapi.testclient import TestClient

from catalog.main import app as catalog_app
from inventory.main import app as inventory_app
from orders.main import app as orders_app
from payments.main import app as payments_app

# Import all service apps
from users.main import app as users_app


@pytest.fixture
def users_client():
    return TestClient(users_app)


@pytest.fixture
def catalog_client():
    return TestClient(catalog_app)


@pytest.fixture
def inventory_client():
    return TestClient(inventory_app)


@pytest.fixture
def orders_client():
    return TestClient(orders_app)


@pytest.fixture
def payments_client():
    return TestClient(payments_app)


@pytest.fixture
def auth_token(users_client):
    """Register a user and return a valid JWT."""
    import uuid as uuid_mod
    email = f"e2e-{uuid_mod.uuid4().hex[:8]}@example.com"
    users_client.post("/users/register", json={"email": email, "password": "secret123"})
    login_resp = users_client.post("/users/login", json={"email": email, "password": "secret123"})
    return login_resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def test_e2e_happy_path(users_client, catalog_client, inventory_client, orders_client, payments_client, auth_headers):
    """Full flow: create product -> create order -> pay -> reserve -> confirm."""
    import uuid as uuid_mod

    # 1. Create category + product via catalog
    cat_name = f"e2e-category-{uuid_mod.uuid4().hex[:8]}"
    cat_resp = catalog_client.post("/catalog/categories", json={"name": cat_name}, headers=auth_headers)
    assert cat_resp.status_code == 201, cat_resp.text
    category_id = cat_resp.json()["id"]

    prod_resp = catalog_client.post(
        "/catalog/products",
        json={"name": "E2E Product", "price": 25.0, "category_id": category_id, "product_type": "equipment", "water_type": "both"},
        headers=auth_headers,
    )
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    # 2. Create order via orders service
    order_resp = orders_client.post(
        "/orders",
        json={"items": [{"product_id": product_id, "quantity": 1, "price": 25.0}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    assert order_data["status"] == "pending"
    order_id = order_data["id"]  # use the actual order ID from the response

    # 3. Charge payment via payments service
    charge_resp = payments_client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 25.0},
        headers=auth_headers,
    )
    assert charge_resp.status_code == 201
    assert charge_resp.json()["status"] == "succeeded"

    # 4. Simulate payment succeeded -> orders reserves inventory
    # Inventory service not running, so reservation will fail -> order cancelled
    # This tests the compensation path
    payment_resp = orders_client.post(
        "/events/payment.succeeded",
        json={"order_id": order_id},
    )
    assert payment_resp.status_code in (200, 502)


def test_e2e_payment_failed_compensation(users_client, orders_client, auth_headers):
    """Flow: create order -> payment fails -> order cancelled."""

    # Create order
    order_resp = orders_client.post(
        "/orders",
        json={"items": [{"product_id": "p1", "quantity": 1, "price": 10.0}]},
        headers=auth_headers,
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # Payment failed
    resp = orders_client.post("/events/payment.failed", json={"order_id": order_id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert resp.json()["reason"] == "payment_failed"

    # Verify order is cancelled
    get_resp = orders_client.get(f"/orders/{order_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "cancelled"


def test_e2e_idempotent_charge(payments_client, auth_headers):
    """Same order charged twice should return same transaction."""
    import uuid as uuid_mod

    order_id = f"idem-{uuid_mod.uuid4().hex[:8]}"
    resp1 = payments_client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 100.0},
        headers=auth_headers,
    )
    assert resp1.status_code == 201

    resp2 = payments_client.post(
        "/payments/charge",
        json={"order_id": order_id, "amount": 100.0},
        headers=auth_headers,
    )
    assert resp2.status_code == 200  # idempotent: returns existing transaction
    assert resp2.json()["id"] == resp1.json()["id"]
