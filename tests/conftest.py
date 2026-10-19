"""Pytest configuration and shared fixtures."""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-32-bytes-minimum!!")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret-32-bytes-minimum!!")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def set_env():
    """Set required env vars for all tests."""
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-32-bytes-minimum!!"
    os.environ["WEBHOOK_SECRET"] = "test-webhook-secret-32-bytes-minimum!!"
    yield
