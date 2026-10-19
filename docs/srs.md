# Software Requirements Specification (SRS)

**Document ID:** SRS-001  
**Status:** DRAFT  
**Linked:** [`BRD`](brd.md), [`PRD`](prd.md), [`USER-STORIES`](user-stories.md), [`USE-CASES`](use-cases.md), [`HLD`](hld.md), [`DATA-OWNERSHIP`](data-ownership.md), [`EVENTS`](events.md), [`API-CONTRACTS`](api-contracts.md), [`SECURITY`](security.md), [`TEST-STRATEGY`](test-strategy.md), [`PLAN.md`](../PLAN.md)

## 1. Functional requirements

| ID | Requirement | Description | Priority | Status | Linked stories | Linked use cases |
|---|---|---|---|---|---|---|
| REQ-001 | User registration & authentication | Register user, issue JWT, validate credentials | Must | CONFIRMED | US-001, US-002 | UC-001, UC-002 |
| REQ-002 | Aquarium product catalog | List products with species/water type/care attributes; filter by water type (freshwater/saltwater) | Must | CONFIRMED | US-003 | UC-003 |
| REQ-003 | Order creation | Create order in `pending` state, publish `order.created` | Must | CONFIRMED | US-004, US-005 | UC-004 |
| REQ-004 | Payment processing | Charge sandbox provider, publish `payment.succeeded`/`payment.failed` | Must | CONFIRMED | US-005, US-006 | UC-005 |
| REQ-005 | Inventory reservation | Reserve stock after payment success; release on failure; track livestock separately | Must | CONFIRMED | US-006 | UC-006 |
| REQ-006 | Order confirmation | Confirm order only after stock reserved + payment captured | Must | CONFIRMED | US-007 | UC-007 |
| REQ-007 | Order cancellation & compensation | Cancel order, refund payment, release stock on failure | Must | CONFIRMED | US-008 | UC-008 |
| REQ-008 | Event reliability | At-least-once delivery, idempotent handlers, bounded retries, dead-letter stream | Must | CONFIRMED | US-005, US-006 | UC-005, UC-006 |
| REQ-009 | Payment security | No card/CVV storage; webhook signature verification; duplicate callback idempotency | Must | CONFIRMED | US-006 | UC-005 |
| REQ-010 | Authorization | Per-service authorization; defense in depth | Must | CONFIRMED | US-001 through US-009 | All |
| REQ-011 | Audit logging | Log auth events, state changes, payment events, DOA claims | Should | CONFIRMED | — | All |
| REQ-012 | DOA claim handling | Livestock reservations can be marked DOA with evidence; compensation processed | Must | CONFIRMED | US-009 | UC-009 |

## 2. Non-functional requirements

| ID | Requirement | Description | Priority | Status |
|---|---|---|---|---|
| NFR-001 | Delivery guarantee | At-least-once via Redis Streams consumer groups + `XACK` | Must | CONFIRMED |
| NFR-002 | Exactly-once processing | Achieved via idempotency keys + transactional outbox | Must | CONFIRMED |
| NFR-003 | Retry policy | N retries per message (N=3), then dead-letter stream | Must | CONFIRMED |
| NFR-004 | Pending recovery | Replay `XPENDING` entries after crash/restart | Must | CONFIRMED |
| NFR-005 | Database isolation | One database per service; no cross-service tables | Must | CONFIRMED |
| NFR-006 | Dev database | SQLite per service; WAL mode recommended | Must | CONFIRMED |
| NFR-007 | Prod database | PostgreSQL per service | Must | CONFIRMED |
| NFR-008 | Communication | Sync HTTP for queries/commands; Redis Streams for async events | Must | CONFIRMED |
| NFR-009 | Gateway routing | Clients call gateway only; never services directly | Must | CONFIRMED |
| NFR-010 | Deployment | Docker Compose | Must | CONFIRMED |
| NFR-011 | Rate limiting | At gateway and per-service | Should | CONFIRMED |
| NFR-012 | Secrets management | Environment variables / Docker secrets; never committed | Must | CONFIRMED |
| NFR-013 | Audit logging | Auth events, order state changes, payment events, DOA claims | Should | CONFIRMED |
| NFR-014 | Vulnerability scanning | Automated dependency + security scans in CI | Should | CONFIRMED |

## 3. Order state machine (from PLAN.md)

```
[pending] --(payment initiated)--> [reserved] --(stock reserved + payment captured)--> [confirmed]
   |                                      |
   |--(any failure)-->                   |--(any failure)--> [cancelled]
   |                                      |
   └--(compensate: refund + release)---> [cancelled]
```

**Rule:** Payment success does **not** automatically confirm an order. Inventory must be reserved first.

## 4. Aquarium-specific state extensions

### DOA (Dead on Arrival) state
```
[confirmed] --(DOA claim filed with evidence)--> [doa_claimed]
[doa_claimed] --(refund processed)--> [refunded]
[doa_claimed] --(replacement shipped)--> [replacement_shipped]
```

## 5. Compensation rules

| Failed step | Compensation actions (in reverse order) |
|---|---|
| Inventory reservation fails after payment | Release payment → cancel order |
| Payment capture fails after stock reserved | Release stock → cancel order |
| Any step fails mid-saga | Reverse all completed steps idempotently |
| DOA claim validated | Refund payment or ship replacement; mark reservation `doa_reported` |

## 6. Open questions
- Exact retry bound N (`DECIDED`: N = 3)
- Is email verification required before login? (`OPEN`)
- DOA claim window: 3 days or 7 days? (`OPEN`)
