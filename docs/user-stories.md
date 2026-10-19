# User Stories

**Document ID:** US-001  
**Status:** DRAFT  
**Linked:** [`PERSONAS`](personas.md), [`USER-JOURNEYS`](user-journeys.md), [`USE-CASES`](use-cases.md), [`SRS`](srs.md), [`TRACEABILITY`](traceability.md)

## Prioritized user stories

| ID | Story | Persona | Priority | Status | Linked use case | Linked requirements | Acceptance criteria |
|---|---|---|---|---|---|---|---|
| US-001 | As a customer, I can register an account so I can sign in and place orders | Sarah | Must | DRAFT | UC-001 | REQ-001 | AC-001, AC-002 |
| US-002 | As a customer, I can sign in with my credentials so I can access my account | Sarah, Marcus | Must | DRAFT | UC-002 | REQ-001 | AC-003, AC-004 |
| US-003 | As a customer, I can browse aquarium products (fish, corals, equipment) with species/water type attributes so I can find suitable items | Sarah, Marcus | Must | DRAFT | UC-003 | REQ-002, REQ-014 | AC-005 |
| US-004 | As a customer, I can create an order for in-stock products so I can purchase them | Sarah | Must | DRAFT | UC-004 | REQ-003 | AC-006, AC-007 |
| US-005 | As a customer, I can pay for my order so the order can be confirmed | Sarah, Marcus | Must | DRAFT | UC-005 | REQ-004 | AC-008, AC-009 |
| US-006 | As a customer, I want inventory reserved before payment is captured so I am not charged for unavailable items | Priya | Must | DRAFT | UC-006 | REQ-005 | AC-010, AC-011 |
| US-007 | As a customer, I can view my order status so I know if it is confirmed or cancelled | Sarah, Marcus, Priya | Must | DRAFT | UC-007 | REQ-006 | AC-013 |
| US-008 | As a customer, I want my order cancelled and payment refunded if stock is unavailable after payment | Priya | Must | DRAFT | UC-008 | REQ-006 | AC-014, AC-015 |
| US-009 | As a customer, I can file a DOA (Dead on Arrival) claim for livestock with photo evidence so I can get a refund or replacement | Priya | Must | DRAFT | UC-009 | REQ-013 | AC-016 |

## Acceptance criteria

| ID | Criterion | Measurable | Verified by |
|---|---|---|---|
| AC-001 | Registration accepts valid email + password | HTTP 201 + JWT returned | TC-001 |
| AC-002 | Registration rejects duplicate email | HTTP 409 | TC-002 |
| AC-003 | Login accepts valid credentials | HTTP 200 + JWT | TC-003 |
| AC-004 | Login rejects invalid credentials | HTTP 401 | TC-004 |
| AC-005 | Product catalog returns paginated list with aquarium attributes | HTTP 200 + items array | TC-005 |
| AC-006 | Order creation sets state `pending` | DB state = `pending` | TC-006 |
| AC-007 | Order creation publishes `order.created` | Redis stream entry exists | TC-007 |
| AC-008 | Payment success publishes `payment.succeeded` | Redis stream entry exists | TC-008 |
| AC-009 | Duplicate webhook callback creates one charge | 1 transaction in DB | TC-009 |
| AC-010 | Inventory reserved only after `payment.succeeded` | No reserve without payment event | TC-010 |
| AC-011 | Reservation failure releases any held stock | Stock available again | TC-011 |
| AC-012 | Order → `confirmed` only after stock reserved + payment captured | DB state = `confirmed` | TC-012 |
| AC-013 | Order status queryable via GET /orders/{id} | HTTP 200 + status field | TC-013 |
| AC-014 | Failure compensation: stock released → payment refunded → order cancelled | Final state = `cancelled` | TC-014 |
| AC-015 | Compensation is idempotent | Replay produces no duplicate side effects | TC-015 |
| AC-016 | DOA claim marks reservation `doa_reported` and publishes `stock.doa_reported` | DB state = `doa_reported` | TC-016 |

## Prioritization method
MoSCoW: All MVP stories are "Must". "Should" and "Could" items deferred to post-MVP.

## Open questions
- Is email verification required before login? (`OPEN`)
- DOA claim window: 3 days or 7 days? (`OPEN`)
