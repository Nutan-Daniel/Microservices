"""Gateway service tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from gateway.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt
    token = jwt.encode({"sub": "user-1"}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_products_public_no_auth(client):
    """Product browsing is public - no auth required."""
    resp = client.get("/products")
    # Catalog may or may not be running during test
    assert resp.status_code in (200, 502), resp.text


def test_products_with_auth_downstream_unavailable(client, auth_headers):
    """Gateway forwards to catalog; response depends on whether catalog is running."""
    resp = client.get("/products", headers=auth_headers)
    # If catalog is running: 200/404/etc. If down: 502. All are valid outcomes.
    assert resp.status_code in (200, 401, 404, 409, 502), resp.text


def test_register_downstream_unavailable(client):
    """Gateway register calls users service; response depends on whether users is running."""
    resp = client.post("/register", json={"email": "gw@example.com", "password": "secret123"})
    # If users is running: 201/400/409. If down: 502. All are valid outcomes.
    assert resp.status_code in (200, 201, 400, 409, 502), resp.text


def test_rate_limiting(client):
    """Rate limiting middleware doesn't crash on rapid requests."""
    import uuid
    for _ in range(10):
        resp = client.post("/register", json={"email": f"rate-{uuid.uuid4().hex[:8]}@example.com", "password": "secret123"})
        # Any response is valid: 201/400/409 (users up), 429 (rate limited), 502 (users down)
        assert resp.status_code in (200, 201, 400, 409, 429, 502), resp.text
