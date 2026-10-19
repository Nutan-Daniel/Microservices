# Aquarium Fish Shop Microservices — Implementation Plan

## Goal
Build a greenfield aquarium fish shop platform as decoupled Python/FastAPI microservices, each owning its data, communicating via synchronous HTTP (queries/commands) and Redis Streams (async events), fronted by a FastAPI API Gateway. All services run in Docker. A dedicated React storefront frontend consumes the gateway.

Domain: aquarium livestock (freshwater & saltwater fish, corals, invertebrates, aquatic plants) + aquarium equipment & supplies.

Key differentiators from generic e-commerce:
- **Live animal guarantee** (DOA protection, live delivery guarantee)
- **Climate-aware shipping** (temperature-controlled, overnight)
- **Species compatibility matrices** & stocking recommendations by tank size
- **WYSIWYG** for unique specimens (corals, rare fish)
- **Real-time inventory** for livestock
- **Care library** (species care guides, water parameter calculators, disease database)

No implementation yet — this plan must be reviewed before any code is written.

## Decisions (locked)
- Domain: aquarium fish shop (freshwater + saltwater fish + equipment & supplies)
- Stack: Python + FastAPI, async
- Communication: hybrid — sync HTTP + Redis Streams events
- Async broker: Redis (Streams + consumer groups)
- Database: one database per service (schema isolation); SQLite for local development, PostgreSQL recommended for production
- API Gateway: FastAPI, clients call gateway only, never services directly
- Deployment: Docker Compose
- Frontend: dedicated React storefront, calls gateway only

## Development Environment
- Python: 3.13.15 (venv active)
- Virtual environment: project-local `.venv` (stdlib `venv`, not committed to git)
- Dev dependencies: `requirements-dev.txt` (ruff, pytest, bandit, pip-audit + FastAPI runtime stack)
- Activation (PowerShell): `.venv\Scripts\Activate.ps1`
- Verification commands:
  - `python -m ruff check .`
  - `python -m pytest`
  - `python -m bandit -r gateway users catalog inventory orders payments shared`
  - `python -m pip_audit`
  - `docker compose config`
  - `trivy --version`

## Service boundaries & data ownership

| Service | Owns | Exposes (HTTP) | Publishes (Redis Stream) |
|---|---|---|---|
| users | users, auth, profiles | register, login, get/profile | user.created, user.updated |
| catalog | products, categories, stock snapshot | list products, get product, search by species/water type | product.created, product.updated, stock.changed |
| inventory | stock reservations/decrements, livestock tracking | reserve, release, check stock | stock.reserved, stock.released, stock.decremented, stock.low |
| orders | orders, order items, order state machine, DOA claims | create order, get order, cancel order, report DOA | order.created, order.paid, order.cancelled, order.doa_claim |
| payments | payment transactions | charge, refund | payment.succeeded, payment.failed |
| gateway | routing only | aggregate endpoints to downstream services | none |
| storefront | UI layer | React SPA calling gateway | none |

## Data flow (sync + async)

Synchronous path (client → gateway → service → client):
- GET /products → gateway → catalog
- POST /orders → gateway → orders (creates order in `pending` state)
- POST /payments → gateway → payments

Async path (Redis Streams consumer groups, at-least-once):
1. orders publishes `order.created` → payments consumes, charges (sandbox provider), publishes `payment.succeeded`/`payment.failed`
2. orders consumes `payment.succeeded` → inventory reserve stock → if success, publish `stock.reserved` and finalize/capture payment; if reservation fails, release payment and publish `order.cancelled`
3. orders transitions order state: pending → reserved → confirmed (or cancelled on failure)
4. Compensating transactions on failure: refund payment → release stock → cancel order
5. Transactional outbox per service: events written to outbox table in same DB transaction as state change; relay publishes to Redis Streams

## Aquarium-specific business rules

### Livestock (live animals)
- Fish, corals, invertebrates, plants are **livestock** — perishable, require climate-aware shipping
- Each livestock item has: species, scientific name, water type (freshwater/saltwater), care level, max size, temperature range, pH range, temperament, diet, origin, compatibility notes
- WYSIWYG flag for unique specimens (corals, rare fish) — once sold, item is removed
- Real-time inventory: livestock availability updated instantly; out-of-stock items not orderable
- DOA (Dead on Arrival) guarantee: customer can report DOA within 3 days with photo/video → exchange or refund

### Equipment & supplies
- Filters, heaters, lights, tanks, stands, substrate, decorations, food, water care products
- Non-perishable, standard shipping
- Attributes: brand, tank size compatibility, power, dimensions, water type compatibility

### Compatibility & stocking
- Species compatibility matrix: which fish can coexist
- Stocking blueprint: recommended stocking levels by tank size
- Water parameter checker: match fish to customer's tank parameters

## Order lifecycle (refined)
A successful payment does **not** automatically confirm an order.

Sequence:
1. Order created in `pending` state.
2. Payment initiated; `payment.succeeded` received.
3. Reserve inventory via inventory-service (livestock checked for availability).
4. On reservation failure: release payment, mark order `cancelled`, publish `order.cancelled`.
5. On reservation success: publish `stock.reserved`, capture/finalize payment.
6. Mark order `confirmed`.

On any failure: compensate in reverse order (release stock, refund payment, cancel order) → `cancelled`. Compensating actions are executed idempotently.

### DOA claim flow
1. Customer receives livestock, finds specimen dead on arrival.
2. Customer submits DOA claim with photo/video evidence within 3 days.
3. orders service validates claim, marks order with `doa_claimed` status.
4. Compensation: refund or replacement shipment arranged.
5. Event `order.doa_claim` published for audit and inventory adjustment.

## Payments (security)
- Payment-provider sandbox (Stripe) initially; no real card data.
- Never store card numbers or CVVs; store only provider reference/token.
- Verify provider webhook signatures on every callback.
- Handle duplicate callbacks idempotently (same payment intent processed once).

## Security
- Centralize identity/authentication at the gateway where useful.
- Enforce authorization in each service too (defense in depth); never trust the gateway alone.
- Rate limiting at gateway and per-service.
- Secrets management: environment variables / Docker secrets, never committed.
- Audit logging: auth events, order state changes, payment events, DOA claims.
- Automated dependency and security scans in CI.

## User interface
- Dedicated React storefront application, separate from the API gateway.
- The gateway is an API facade for the storefront and other clients, not the customer application itself.
- Storefront features: species browse by water type, compatibility checker, care guides, WYSIWYG specimen gallery, stocking calculator.

## File structure
```
C:\Development\Microservices\
├── docker-compose.yml
├── .env.example
├── README.md
├── PLAN.md
├── gateway/                # FastAPI gateway
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── users/                  # users service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── users.db            # SQLite (dev) / PostgreSQL (prod)
├── catalog/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── catalog.db
├── inventory/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── inventory.db
├── orders/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── orders.db
├── payments/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── payments.db
├── storefront/             # Dedicated React storefront UI
│   ├── Dockerfile
│   ├── package.json
│   └── src/
└── shared/                 # redis client helpers, models, event schemas, outbox relay
    ├── __init__.py
    ├── events.py
    ├── outbox.py
    └── consumer.py
```

## Implementation task list (ordered)
1. ✅ Scaffold repo: docker-compose.yml (Redis + 6 service containers + storefront), .env.example, shared package with Redis stream publisher/consumer helpers, Pydantic event schemas, transactional outbox relay, DLQ handling
2. ✅ users service: DB schema (users), register/login endpoints, publish user.created, JWT issuance
3. ✅ catalog service: DB schema (products, categories, fish attributes, equipment attributes), CRUD endpoints, publish product events
4. ✅ inventory service: DB schema (stock reservations, livestock tracking), reserve/release/check endpoints, publish stock events
5. ✅ orders service: DB schema (orders, order_items, DOA claims), state machine (pending→reserved→confirmed→cancelled), consume payment.succeeded/failed, publish order events, idempotency checks
6. ✅ payments service: DB schema (transactions), charge/refund endpoints, consume order.created, publish payment events, sandbox provider integration, webhook verification
7. ✅ gateway service: FastAPI routes proxying to each service, auth centralization, rate limiting, health endpoint
8. ✅ storefront: dedicated React UI consuming gateway endpoints
9. Wire docker-compose networks, env vars (REDIS_URL, DB URLs, downstream URLs, provider keys), `depends_on` + restart policies
10. Add idempotency keys + consumer group ack handling + pending-message recovery + bounded retries + DLQ in all async consumers
11. Add health checks, audit logging, secrets management, automated dependency/security scans
12. Validation: `docker compose up -d`; E2E create product → create order → pay → reserve stock → confirm order; failure compensation path; idempotency replay; DOA claim flow

## Testing stage (complete)
- 49 tests across 6 test files: test_users, test_catalog, test_inventory, test_orders, test_payments, test_gateway, test_e2e
- All quality gates pass: ruff, bandit, pip-audit, docker compose config
- Test coverage: user auth, CRUD per service, payment idempotency, webhook dedup, order state machine, compensation path, E2E happy path, gateway downstream failure handling

## Issues & fixes (encountered during implementation)

| Issue | Root cause | Fix |
|---|---|---|
| pydantic-core build failed | Python 3.14 lacks pre-built Rust wheels; MSVC linker missing | Switched venv to Python 3.13 (pre-built cp313 wheels) |
| passlib/bcrypt crash | bcrypt backend broken on Python 3.13 | Replaced passlib with stdlib `hashlib.pbkdf2_hmac` (PBKDF2-SHA256, 100k iterations) |
| Register returned 500 without Redis | Outbox relay hard-failed when Redis unavailable | Made Redis publishing non-fatal; event sits in outbox table for later replay |
| `EmailStr` ImportError | `email-validator` package not installed | Replaced `EmailStr` with plain `str` + inline email format check |
| `aiosqlite` ModuleNotFoundError | Async SQLite driver not installed; code used sync SQLAlchemy | Changed DB URL to sync `sqlite:///` |
| JWT 401 / key length warning | Default secret 20 bytes < PyJWT 32-byte minimum for HS256 | Require `JWT_SECRET_KEY` of 32+ bytes |
| `get_redis()` coroutine not awaited | `_publish_event` used `asyncio.run()` inside sync function | Made `_publish_event` async with proper `await` |
| `declarative_base()` deprecated | SQLAlchemy 2.0 moved to `sqlalchemy.orm` | Import from `sqlalchemy.orm` instead of `sqlalchemy.ext.declarative` |
| `on_event` deprecated | FastAPI deprecated `@app.on_event` | Removed empty startup/shutdown handlers |

## Development environment status
- Python 3.13.15 venv (`.venv`) — active
- ruff 0.16.10, pytest 9.1.1, bandit 1.7.10, pip-audit 2.10.1 — all pass
- FastAPI 0.146.0, starlette 1.3.1, SQLAlchemy 2.0.55, Redis 5.3.1, PyJWT 2.15.1
- docker-compose.yml validated; Docker 29.8.2, Compose v5.6.0

## Validation steps
- `docker compose up -d` starts all services + Redis + storefront
- `curl gateway/health` returns 200
- End-to-end: create product → create order → pay → stock reserved → order confirmed, verifying each service DB and Redis stream entries
- Failure: simulate payment failure → order cancelled → stock released → payment refunded
- Idempotency: replay same orderId event → no duplicate charge
- Webhook duplicate callback: no duplicate payment transaction
- DOA claim: submit claim with evidence → order marked doa_claimed → compensation processed

## Risks / open questions
- SQLite write concurrency under async consumers (single writer per service file; WAL mode recommended; PostgreSQL for production)
- No distributed transaction coordinator — sagas rely on compensating transactions; partial failures handled via compensations and retries
- No service discovery; services address each other by Docker Compose service names via env vars
- Auth: gateway centralizes identity; each service enforces authorization (defense in depth)
- Secrets: never commit provider keys or DB credentials; use env vars/secrets
- Storefront framework: React selected
- Payment provider: Stripe sandbox selected
- Exact retry bound N: 3
- JWT access token TTL: 60 minutes
- Email verification before login: Not implemented (MVP)
- Production deployment target: Docker Compose on single VM
- CI platform / container registry: GitHub Actions + ghcr.io