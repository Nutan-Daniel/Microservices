"""Users service tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from users.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _unique_email(prefix="test"):
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def test_register(client):
    resp = client.post("/users/register", json={"email": _unique_email("alice"), "password": "secret123"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client):
    email = _unique_email("bob")
    client.post("/users/register", json={"email": email, "password": "secret123"})
    resp = client.post("/users/register", json={"email": email, "password": "secret123"})
    assert resp.status_code == 409


def test_register_invalid_email(client):
    resp = client.post("/users/register", json={"email": "not-an-email", "password": "secret123"})
    assert resp.status_code == 400


def test_login(client):
    email = _unique_email("carol")
    client.post("/users/register", json={"email": email, "password": "secret123"})
    resp = client.post("/users/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    email = _unique_email("dave")
    client.post("/users/register", json={"email": email, "password": "secret123"})
    resp = client.post("/users/login", json={"email": email, "password": "wrong"})
    assert resp.status_code == 401


def test_profile(client):
    email = _unique_email("eve")
    client.post("/users/register", json={"email": email, "password": "secret123"})
    login_resp = client.post("/users/login", json={"email": email, "password": "secret123"})
    token = login_resp.json()["access_token"]

    resp = client.get("/users/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == email


def test_profile_no_token(client):
    resp = client.get("/users/profile")
    assert resp.status_code == 401


def test_profile_wrong_token(client):
    resp = client.get("/users/profile", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401
