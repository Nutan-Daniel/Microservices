# Use Cases

**Document ID:** UC-001  
**Status:** DRAFT  
**Linked:** [`USER-JOURNEYS`](user-journeys.md), [`USER-STORIES`](user-stories.md), [`SRS`](srs.md), [`HLD`](hld.md)

## UC-001: Register customer

| Field | Value |
|---|---|
| Actor | Unregistered customer |
| Preconditions | None |
| Postconditions | Customer account exists; JWT issued |
| Trigger | Customer submits registration form |
| Main flow | 1. Customer submits email + password → gateway → users service 2. users validates input 3. users creates account 4. users issues JWT 5. gateway returns JWT + profile |
| Alternative flows | A1: Email already registered → error 409; A2: Invalid input → error 400 |
| Linked stories | US-001 |
| Linked requirements | REQ-001 |
| Acceptance criteria | AC-001, AC-002 |

## UC-002: Authenticate customer

| Field | Value |
|---|---|
| Actor | Registered customer |
| Preconditions | Account exists |
| Postconditions | Valid JWT session |
| Trigger | Customer submits login credentials |
| Main flow | 1. Customer submits credentials → gateway → users 2. users validates credentials 3. users issues JWT 4. gateway returns JWT |
| Alternative flows | A1: Invalid credentials → error 401 |
| Linked stories | US-002 |
| Linked requirements | REQ-001 |
| Acceptance criteria | AC-003, AC-004 |

## UC-003: Browse aquarium product catalog

| Field | Value |
|---|---|
| Actor | Authenticated customer |
| Preconditions | Valid JWT |
| Postconditions | Product list returned |
| Trigger | Customer requests product list |
| Main flow | 1. Customer requests products → gateway → catalog 2. catalog returns products with aquarium attributes |
| Linked stories | US-003 |
| Linked requirements | REQ-002 |
| Acceptance criteria | AC-005 |

## UC-004: Create order

| Field | Value |
|---|---|
| Actor | Authenticated customer |
| Preconditions | Valid JWT; product in stock |
| Postconditions | Order in `pending` state; `order.created` published |
| Trigger | Customer submits order |
| Main flow | 1. Customer submits order → gateway → orders 2. orders creates order in `pending` 3. orders publishes `order.created` → Redis Streams 4. gateway returns order ID + status |
| Alternative flows | A1: Product out of stock → error 409 |
| Linked stories | US-004, US-005 |
| Linked requirements | REQ-003 |
| Acceptance criteria | AC-006, AC-007 |

## UC-005: Pay for order

| Field | Value |
|---|---|
| Actor | Authenticated customer / payments service |
| Preconditions | Order in `pending`; `payment.succeeded` or `payment.failed` event |
| Postconditions | Payment transaction recorded; order moves toward `confirmed` or `cancelled` |
| Trigger | `order.created` event consumed by payments |
| Main flow | 1. payments consumes `order.created` 2. payments charges sandbox provider 3. payments publishes `payment.succeeded` or `payment.failed` 4. orders consumes result |
| Alternative flows | A1: Provider error → `payment.failed`; A2: Duplicate webhook → idempotent no-op |
| Linked stories | US-005, US-006 |
| Linked requirements | REQ-004, REQ-005 |
| Acceptance criteria | AC-008, AC-009, AC-010 |

## UC-006: Reserve inventory (livestock or equipment)

| Field | Value |
|---|---|
| Actor | orders service / inventory service |
| Preconditions | `payment.succeeded` received |
| Postconditions | Stock reserved or release attempted |
| Trigger | `payment.succeeded` event consumed by orders |
| Main flow | 1. orders requests reserve → inventory 2. inventory reserves stock 3. inventory publishes `stock.reserved` |
| Alternative flows | A1: Insufficient stock → inventory publishes release / no reserve; orders compensates |
| Linked stories | US-006 |
| Linked requirements | REQ-005 |
| Acceptance criteria | AC-011, AC-012 |

## UC-007: Confirm order

| Field | Value |
|---|---|
| Actor | orders service |
| Preconditions | `stock.reserved` received; payment captured |
| Postconditions | Order → `confirmed` |
| Trigger | `stock.reserved` + payment capture success |
| Main flow | 1. orders captures/finalizes payment 2. orders transitions to `confirmed` 3. orders publishes order confirmation |
| Linked stories | US-007 |
| Linked requirements | REQ-006 |
| Acceptance criteria | AC-013 |

## UC-008: Cancel order (failure compensation)

| Field | Value |
|---|---|
| Actor | orders service |
| Preconditions | Order in `pending` or `reserved`; failure detected |
| Postconditions | Order → `cancelled`; compensations executed |
| Trigger | Reservation failure or payment failure |
| Main flow | 1. orders releases stock (if reserved) 2. orders refunds payment (if charged) 3. orders transitions to `cancelled` 4. orders publishes `order.cancelled` |
| Linked stories | US-008 |
| Linked requirements | REQ-006 |
| Acceptance criteria | AC-014, AC-015 |

## UC-009: File DOA claim for livestock

| Field | Value |
|---|---|
| Actor | Authenticated customer |
| Preconditions | Order contains livestock; reservation exists |
| Postconditions | Reservation marked `doa_reported`; `stock.doa_reported` published |
| Trigger | Customer submits DOA claim with photo evidence |
| Main flow | 1. Customer submits DOA claim → gateway → inventory 2. inventory validates reservation is livestock 3. inventory marks `doa_reported` 4. inventory publishes `stock.doa_reported` |
| Alternative flows | A1: Reservation not livestock → error 400; A2: DOA already reported → error 400 |
| Linked stories | US-008 |
| Linked requirements | REQ-007 |
| Acceptance criteria | AC-016 |

## Open questions
- Is cart functionality part of UC-003/UC-004, or a separate service? (`OPEN` — catalog owns stock snapshot only; cart not in PLAN.md)
- DOA claim window: 3 days or 7 days? (`OPEN`)
