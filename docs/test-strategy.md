# Test Strategy, Test Plan, and Automated Quality Gates

**Document ID:** TEST-001  
**Status:** DRAFT  
**Linked:** [`SRS`](srs.md), [`USER-STORIES`](user-stories.md), [`USE-CASES`](use-cases.md), [`PLAN.md`](../PLAN.md), [`SECURITY`](security.md)

## 1. Test pyramid

| Layer | Scope | Tool | Examples |
|---|---|---|---|
| Unit | Single function/class | pytest | Password hashing, idempotency check, state transition |
| Integration | Service + DB + Redis | pytest + pytest-asyncio | Register user end-to-end; create order + publish event |
| Contract | HTTP API | pytest + httpx | Gateway routes; service endpoints return correct status |
| E2E | Full stack (docker compose) | pytest + httpx | Create product → create order → pay → reserve → confirm; DOA claim flow |
| Security | SAST + dependency scan | bandit + pip-audit | No hard-coded secrets; no vulnerable deps |

## 2. Test plan by requirement

| TC ID | Requirement | Test type | Description | Pass criterion |
|---|---|---|---|---|
| TC-001 | REQ-001 (register) | Integration | POST /users/register with valid input | HTTP 201; user in DB; JWT issued |
| TC-002 | REQ-001 (register dup) | Integration | POST /users/register with duplicate email | HTTP 409; no duplicate user |
| TC-003 | REQ-001 (login valid) | Integration | POST /users/login with valid credentials | HTTP 200; valid JWT |
| TC-004 | REQ-001 (login invalid) | Integration | POST /users/login with wrong password | HTTP 401 |
| TC-005 | REQ-002 (catalog) | Integration | GET /catalog/products | HTTP 200; paginated list with aquarium attributes |
| TC-006 | REQ-003 (order create) | Integration | POST /orders with valid items | HTTP 201; state `pending`; `order.created` in Redis |
| TC-007 | REQ-004 (payment success) | E2E | Pay for order; `payment.succeeded` published | Redis event; DB transaction |
| TC-008 | REQ-004 (duplicate webhook) | E2E | Send same webhook twice | 1 transaction only |
| TC-009 | REQ-005 (inventory reserve) | E2E | After payment success, stock reserved | `stock.reserved` event; stock decremented |
| TC-010 | REQ-005 (reserve fail) | E2E | Insufficient stock; compensation runs | Order → `cancelled`; payment refunded |
| TC-011 | REQ-006 (confirm) | E2E | Stock reserved + payment captured → `confirmed` | DB state `confirmed` |
| TC-012 | REQ-007 (cancel) | E2E | Failure mid-saga → `cancelled` | Compensations run; final state `cancelled` |
| TC-013 | REQ-008 (idempotency) | Integration | Replay same orderId event | No duplicate state mutation |
| TC-014 | REQ-008 (DLQ) | Integration | Message exceeding retry bound | Message in DLQ stream |
| TC-015 | REQ-009 (no card data) | Security | Scan DB + code for card patterns | 0 matches |
| TC-016 | REQ-010 (authZ) | Integration | Call service without valid JWT | HTTP 401 |
| TC-016b | REQ-012 (DOA claim) | Integration | Report DOA for livestock reservation | Reservation → `doa_reported`; event published |

## 3. Quality gates (must pass before merge / release)

| Gate | Tool | Command | Threshold |
|---|---|---|---|
| Lint | ruff | `python -m ruff check .` | 0 errors |
| Format check | ruff | `python -m ruff format --check .` | 0 differences |
| Security SAST | bandit | `python -m bandit -r gateway users catalog inventory orders payments shared` | 0 high/medium issues |
| Dependency scan | pip-audit | `python -m pip_audit` | 0 known-vulnerable packages |
| Unit tests | pytest | `python -m pytest` | 100% pass |
| Compose validation | docker compose | `docker compose config --quiet` | Exit 0 |
| Image scan | trivy | `trivy image ` | 0 critical/high vulnerabilities (`OPEN` — Trivy optional) |

## 4. Test environment
- Python 3.13 virtual environment (`.venv`)
- SQLite for service DBs in test
- Redis for event streams in test
- Docker Compose for E2E stack

## 5. Open questions
- Test coverage threshold (% lines/branches)? (`OPEN`)
- E2E test frequency: every PR or nightly? (`OPEN`)
