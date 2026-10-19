"""Catalog service tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from catalog.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt
    token = jwt.encode({"sub": "user-1"}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _unique_name(prefix="test"):
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_create_category(client, auth_headers):
    resp = client.post("/catalog/categories", json={"name": _unique_name("electronics")}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data


def test_create_duplicate_category(client, auth_headers):
    name = _unique_name("books")
    client.post("/catalog/categories", json={"name": name}, headers=auth_headers)
    resp = client.post("/catalog/categories", json={"name": name}, headers=auth_headers)
    assert resp.status_code == 409


def test_list_categories(client, auth_headers):
    client.post("/catalog/categories", json={"name": _unique_name("clothing")}, headers=auth_headers)
    resp = client.get("/catalog/categories", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_create_product(client, auth_headers):
    cat_resp = client.post("/catalog/categories", json={"name": _unique_name("gadgets")}, headers=auth_headers)
    assert cat_resp.status_code == 201, cat_resp.text
    category_id = cat_resp.json()["id"]

    resp = client.post(
        "/catalog/products",
        json={"name": "Widget", "description": "A test widget", "price": 19.99, "category_id": category_id, "product_type": "equipment", "water_type": "both"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Widget"
    assert data["price"] == 19.99
    assert data["category_id"] == category_id


def test_list_products(client, auth_headers):
    resp = client.get("/catalog/products", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_product(client, auth_headers):
    cat_resp = client.post("/catalog/categories", json={"name": _unique_name("tools")}, headers=auth_headers)
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    prod_resp = client.post(
        "/catalog/products",
        json={"name": "Hammer", "price": 9.99, "category_id": category_id, "product_type": "equipment", "water_type": "both"},
        headers=auth_headers,
    )
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    resp = client.get(f"/catalog/products/{product_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Hammer"


def test_get_product_not_found(client, auth_headers):
    resp = client.get("/catalog/products/nonexistent-id", headers=auth_headers)
    assert resp.status_code == 404


def test_check_stock(client, auth_headers):
    resp = client.get("/inventory/stock/some-product", headers=auth_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "product_id" in data
        assert "available_quantity" in data


def test_no_token(client):
    resp = client.post("/catalog/categories", json={"name": "x"})
    assert resp.status_code == 401
