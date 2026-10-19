# High-Level Design (HLD)

**Document ID:** HLD-001  
**Status:** DRAFT  
**Locked decisions:** Preserved from [`PLAN.md`](../PLAN.md)  
**Linked:** [`SRS`](srs.md), [`DATA-OWNERSHIP`](data-ownership.md), [`API-CONTRACTS`](api-contracts.md), [`EVENTS`](events.md), [`PLAN.md`](../PLAN.md)

## 1. Architecture overview

Hybrid synchronous/asynchronous microservices architecture for an aquarium fish shop. Clients (React storefront) call a FastAPI API Gateway, which routes to service APIs. Services publish events to Redis Streams via consumer groups for async coordination. Each service owns its database (SQLite dev, PostgreSQL prod).

```
┌─────────────┐      HTTP (sync)       ┌──────────────┐
│  Storefront │───────────────────────>│   Gateway    │
│   (React)   │                        │   (FastAPI)  │
└─────────────┘                        └──────┬───────┘
                                              │
              ┌───────────────┬───────────────┼───────────────┬───────────────┐
              │               │               │               │               │
              ▼               ▼               ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
        │  users  │     │  catalog│     │ inventory│     │  orders │     │ payments│
        │ service │     │ service │     │ service  │     │ service │     │ service │
        └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘
             │               │               │               │               │
             ▼               ▼               ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
        │users.db │     │catalog.db│    │inventory.db│   │orders.db│    │payments.db│
        │(SQLite/ │     │(SQLite/ │    │(SQLite/   │     │(SQLite/ │     │(SQLite/ │
        │ PG)     │     │ PG)     │    │ PG)       │     │ PG)     │     │ PG)     │
        └─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
             │               │               │               │               │
             └───────────────┴───────────────┴───────────────┴───────────────┘
                                                     │
                                          ┌────────▼────────┐
                                          │   Redis Streams │
                                          │ (consumer groups│
                                          │  + outbox + DLQ)│
                                          └─────────────────┘
```

## 2. Service boundaries (locked from PLAN.md)

| Service | Owns | Exposes (HTTP) | Publishes (Redis Stream) |
|---|---|---|---|
| users | users, auth, profiles | register, login, get/profile | user.created, user.updated |
| catalog | products, categories, stock snapshot | list products, get product, search by species/water type | product.created, product.updated, stock.changed |
| inventory | stock reservations/decrements, livestock tracking, DOA | reserve, release, check stock, report DOA | stock.reserved, stock.released, stock.decremented, stock.doa_reported |
| orders | orders, order items, order state machine, DOA claims | create order, get order, cancel order | order.created, order.paid, order.cancelled, order.doa_claim |
| payments | payment transactions | charge, refund | payment.succeeded, payment.failed |
| gateway | routing only | aggregate endpoints to downstream services | none |
| storefront | UI layer (React) | SPA pages calling gateway | none |

**Rule:** One database per service. No cross-service tables, no shared schemas.

## 3. Data flow

### Synchronous path (client → gateway → service → client)
- GET /products → gateway → catalog
- POST /orders → gateway → orders (creates order in `pending` state)
- POST /payments → gateway → payments

### Async path (Redis Streams consumer groups, at-least-once)
1. orders publishes `order.created` → payments consumes, charges (sandbox provider), publishes `payment.succeeded`/`payment.failed`
2. orders consumes `payment.succeeded` → inventory reserve stock → if success, publish `stock.reserved` and finalize/capture payment; if reservation fails, release payment and publish `order.cancelled`
3. orders transitions order state: pending → reserved → confirmed (or cancelled on failure)
4. Compensating transactions on failure: refund payment → release stock → cancel order
5. Transactional outbox per service: events written to outbox table in same DB transaction as state change; relay publishes to Redis Streams

## 4. Event delivery guarantees

| Guarantee | Mechanism |
|---|---|
| At-least-once delivery | Redis Streams consumer groups + explicit `XACK` after successful processing |
| Exactly-once processing | Idempotency keys (`orderId` dedup key) + transactional outbox |
| Pending recovery | Replay `XPENDING` entries after crash/restart |
| Bounded retries | N retries per message (N=3), then dead-letter stream |
| No silent drops | Dead-letter stream retained for inspection/replay |

## 5. Security model (defense in depth)

- **Gateway:** Centralizes identity/authentication (JWT validation, user context injection)
- **Each service:** Enforces its own authorization; never trusts gateway alone
- **Rate limiting:** At gateway and per-service
- **Secrets:** Environment variables / Docker secrets; never committed
- **Audit logging:** Auth events, order state changes, payment events, DOA claims
- **Payments:** Sandbox provider; no card/CVV storage; webhook signature verification; duplicate callback idempotency

## 6. Open questions
- Production deployment target (Docker Compose is dev; prod target undefined) (`OPEN`)
- Service discovery mechanism for production (`OPEN` — PLAN.md uses Docker Compose service names via env vars)
- DOA claim window: 3 days or 7 days? (`OPEN`)
