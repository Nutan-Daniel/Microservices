# API Contracts

**Document ID:** API-001  
**Status:** DRAFT  
**Linked:** [`HLD`](hld.md), [`USE-CASES`](use-cases.md), [`PLAN.md`](../PLAN.md)

## Convention
All services return JSON. Errors use RFC 7807 `application/problem+json` where practical. Base path per service; gateway aggregates at `/`.

## Users service (`/users`)

| Method | Path | Description | Auth | Status |
|---|---|---|---|---|
| POST | /users/register | Register new user | None | 201 / 400 / 409 |
| POST | /users/login | Authenticate, issue JWT | None | 200 / 401 |
| GET | /users/profile | Get current user profile | JWT | 200 / 401 |

## Catalog service (`/catalog`)

| Method | Path | Description | Auth | Status |
|---|---|---|---|---|
| GET | /catalog/products | List products (paginated, filterable by water_type/product_type) | JWT | 200 |
| GET | /catalog/products/{id} | Get product detail with aquarium attributes | JWT | 200 / 404 |
| POST | /catalog/products | Create product (fish, coral, equipment, supply) | JWT | 201 / 400 |
| POST | /catalog/categories | Create category | JWT | 201 / 409 |
| GET | /catalog/categories | List categories | JWT | 200 |

## Inventory service (`/inventory`)

| Method | Path | Description | Auth | Status |
|---|---|---|---|---|
| POST | /inventory/reserve | Reserve stock (livestock or equipment) | JWT (service-to-service) | 200 / 409 |
| POST | /inventory/release | Release reserved stock | JWT (service-to-service) | 200 |
| GET | /inventory/stock/{product_id} | Check available stock | JWT | 200 |
| GET | /inventory/reservations/{order_id} | List reservations for an order | JWT | 200 |
| POST | /inventory/reservations/{reservation_id}/doa | Report Dead on Arrival for livestock | JWT | 200 / 400 / 404 |

## Orders service (`/orders`)

| Method | Path | Description | Auth | Status |
|---|---|---|---|---|
| POST | /orders | Create order (state `pending`) | JWT | 201 / 400 / 409 |
| GET | /orders/{id} | Get order + status | JWT | 200 / 404 |
| POST | /orders/{id}/cancel | Cancel order | JWT | 200 / 400 / 409 |
| POST | /events/payment.succeeded | Async: payment succeeded → reserve inventory | Internal | 200 / 502 |
| POST | /events/payment.failed | Async: payment failed → cancel order | Internal | 200 |

## Payments service (`/payments`)

| Method | Path | Description | Auth | Status |
|---|---|---|---|---|
| POST | /payments/charge | Charge payment (sandbox Stripe) | JWT (service-to-service) | 200 / 400 |
| POST | /payments/refund | Refund payment | JWT (service-to-service) | 200 / 400 |
| POST | /payments/webhook | Provider callback (signature-verified) | None (signature) | 200 |
| GET | /payments/{id} | Get payment | JWT | 200 / 404 |
| GET | /payments/order/{order_id} | List payments for an order | JWT | 200 |

## Gateway (`/`)

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | /register | → users/register | None |
| POST | /login | → users/login | None |
| GET | /profile | → users/profile | JWT |
| GET | /products | → catalog/products | JWT |
| GET | /products/{id} | → catalog/products/{id} | JWT |
| POST | /orders | → orders/create | JWT |
| GET | /orders/{id} | → orders/{id} | JWT |
| POST | /orders/{id}/cancel | → orders/{id}/cancel | JWT |
| POST | /payments/charge | → payments/charge | JWT |
| POST | /payments/refund | → payments/refund | JWT |
| POST | /payments/webhook | → payments/webhook | None (signature) |
| GET | /health | Health check | None |

## Storefront
Consumes gateway endpoints only. No direct service calls.

## Open questions
- Exact request/response JSON schemas (deferred to service implementation) (`OPEN`)
- Pagination parameters for product list (`OPEN`)
