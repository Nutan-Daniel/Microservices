"""API Gateway - routes client requests to downstream services, centralizes auth, rate limiting."""

import json
import os
import time
from collections import defaultdict

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
USERS_URL = os.getenv("USERS_URL", "http://localhost:8001")
CATALOG_URL = os.getenv("CATALOG_URL", "http://localhost:8002")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:8003")
ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:8004")
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://localhost:8005")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):  # noqa: B008
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per client IP)
# ---------------------------------------------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60
    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if t > window_start]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _rate_limit_store[client_ip].append(now)


# ---------------------------------------------------------------------------
# HTTP client (per request - avoids event loop issues with TestClient)
# ---------------------------------------------------------------------------
async def get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="api-gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _forward_response(resp: httpx.Response) -> Response:
    """Forward upstream response preserving status code and JSON body."""
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return Response(
        content=json.dumps(body) if not isinstance(body, str) else body,
        status_code=resp.status_code,
        media_type="application/json",
    )


async def _forward_request(method: str, url: str, client: httpx.AsyncClient, **kwargs) -> Response:
    """Forward request to downstream service; return 502 on connection error."""
    try:
        if method == "GET":
            resp = await client.get(url, **kwargs)
        elif method == "POST":
            resp = await client.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        return _forward_response(resp)
    except httpx.RequestError:
        return Response(
            content=json.dumps({"detail": "Downstream service unavailable"}),
            status_code=502,
            media_type="application/json",
        )
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Users (public + auth)
# ---------------------------------------------------------------------------
@app.post("/register")
async def register(request: Request, client: httpx.AsyncClient = Depends(get_client)):  # noqa: B008
    rate_limit(request)
    body = await request.json()
    return await _forward_request("POST", f"{USERS_URL}/users/register", client, json=body)


@app.post("/login")
async def login(request: Request, client: httpx.AsyncClient = Depends(get_client)):  # noqa: B008
    rate_limit(request)
    body = await request.json()
    return await _forward_request("POST", f"{USERS_URL}/users/login", client, json=body)


@app.get("/profile")
async def profile(request: Request, client: httpx.AsyncClient = Depends(get_client),
                  current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    auth_header = request.headers.get("authorization", "")
    return await _forward_request(
        "GET", f"{USERS_URL}/users/profile", client,
        headers={"Authorization": auth_header},
    )


# ---------------------------------------------------------------------------
# Catalog (auth)
# ---------------------------------------------------------------------------
@app.get("/products")
async def list_products(request: Request, client: httpx.AsyncClient = Depends(get_client),
                        current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    auth_header = request.headers.get("authorization", "")
    return await _forward_request(
        "GET", f"{CATALOG_URL}/catalog/products", client,
        headers={"Authorization": auth_header},
    )


@app.get("/products/{product_id}")
async def get_product(product_id: str, request: Request, client: httpx.AsyncClient = Depends(get_client),
                      current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    auth_header = request.headers.get("authorization", "")
    return await _forward_request(
        "GET", f"{CATALOG_URL}/catalog/products/{product_id}", client,
        headers={"Authorization": auth_header},
    )


# ---------------------------------------------------------------------------
# Orders (auth)
# ---------------------------------------------------------------------------
@app.post("/orders")
async def create_order(request: Request, client: httpx.AsyncClient = Depends(get_client),
                       current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    body = await request.json()
    return await _forward_request(
        "POST", f"{ORDERS_URL}/orders", client, json=body,
        headers={"Authorization": request.headers.get("authorization", "")},
    )


@app.get("/orders")
async def list_orders(request: Request, client: httpx.AsyncClient = Depends(get_client),
                      current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    auth_header = request.headers.get("authorization", "")
    return await _forward_request(
        "GET", f"{ORDERS_URL}/orders", client,
        headers={"Authorization": auth_header},
    )


@app.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request, client: httpx.AsyncClient = Depends(get_client),
                    current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    auth_header = request.headers.get("authorization", "")
    return await _forward_request(
        "GET", f"{ORDERS_URL}/orders/{order_id}", client,
        headers={"Authorization": auth_header},
    )


@app.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, request: Request, client: httpx.AsyncClient = Depends(get_client),
                       current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    auth_header = request.headers.get("authorization", "")
    return await _forward_request(
        "POST", f"{ORDERS_URL}/orders/{order_id}/cancel", client,
        headers={"Authorization": auth_header},
    )


# ---------------------------------------------------------------------------
# Payments (auth)
# ---------------------------------------------------------------------------
@app.post("/payments/charge")
async def charge(request: Request, client: httpx.AsyncClient = Depends(get_client),
                 current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    body = await request.json()
    return await _forward_request(
        "POST", f"{PAYMENTS_URL}/payments/charge", client, json=body,
        headers={"Authorization": request.headers.get("authorization", "")},
    )


@app.post("/payments/refund")
async def refund(request: Request, client: httpx.AsyncClient = Depends(get_client),
                 current_user: str = Depends(get_current_user)):  # noqa: B008
    rate_limit(request)
    body = await request.json()
    return await _forward_request(
        "POST", f"{PAYMENTS_URL}/payments/refund", client, json=body,
        headers={"Authorization": request.headers.get("authorization", "")},
    )


@app.post("/payments/webhook")
async def payments_webhook(request: Request, client: httpx.AsyncClient = Depends(get_client)):
    """Webhook is public (signature-verified by payments service)."""
    body = await request.body()
    headers = {"stripe-signature": request.headers.get("stripe-signature", "")}
    return await _forward_request(
        "POST", f"{PAYMENTS_URL}/payments/webhook", client, content=body, headers=headers,
    )