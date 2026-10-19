# User Journeys

**Document ID:** UJ-001  
**Status:** DRAFT  
**Linked:** [`PERSONAS`](personas.md), [`USE-CASES`](use-cases.md), [`USER-STORIES`](user-stories.md), [`SRS`](srs.md)

## Journey 1: Happy path — purchase fish and equipment

**Persona:** Sarah (beginner freshwater hobbyist)

| Step | Action | System response | Touchpoint |
|---|---|---|---|
| 1 | Register account | Account created, JWT issued | Storefront → gateway → users |
| 2 | Sign in | Authenticated session | Storefront → gateway → users |
| 3 | Browse freshwater fish | Fish list with species, care level, water params returned | Storefront → gateway → catalog |
| 4 | Select beginner fish | Product detail with care level, temperament, compatibility | Storefront → gateway → catalog |
| 5 | Select equipment (filter, heater) | Equipment list returned | Storefront → gateway → catalog |
| 6 | Create order | Order in `pending` state; `order.created` published | Storefront → gateway → orders → Redis Streams |
| 7 | Payment processed | `payment.succeeded` published | payments → Redis Streams → orders |
| 8 | Inventory reserved | `stock.reserved` published; order → `reserved` | orders → inventory → Redis Streams |
| 9 | Payment captured | Order → `confirmed` | orders → payments → Redis Streams |
| 10 | Order confirmation shown | Order status `confirmed` | Storefront → gateway → orders |

**Success criteria:** Order reaches `confirmed` state; customer sees confirmation; each service DB reflects final state; Redis Streams has all events with `XACK`.

## Journey 2: DOA claim — livestock arrives dead

**Persona:** Priya (customer with DOA claim)

| Step | Action | System response | Touchpoint |
|---|---|---|---|
| 1 | Receive livestock order | Package delivered with fish | Delivery carrier |
| 2 | Find specimen dead | Customer photos evidence | Customer |
| 3 | File DOA claim | Claim submitted with photo evidence; reservation marked `doa_reported` | Storefront → gateway → inventory → Redis Streams |
| 4 | Claim validated | Order marked `doa_claimed`; compensation initiated | orders → payments → Redis Streams |
| 5 | Customer notified | Refund or replacement arranged | Storefront → gateway → orders |

**Success criteria:** Reservation marked `doa_reported`; `stock.doa_reported` event published; customer receives refund or replacement.

## Journey 3: Duplicate payment webhook callback

**Persona:** Marcus (experienced reef keeper)

| Step | Action | System response | Touchpoint |
|---|---|---|---|
| 1 | Payment provider sends callback | First callback processed; payment recorded | payments → Redis Streams |
| 2 | Same callback sent again (duplicate) | Idempotency key match; no duplicate charge | payments (idempotency check) |

**Success criteria:** One payment transaction only; no duplicate charge; second callback acknowledged without side effects.

## Open questions
- What is the customer-facing refund timeline SLA? (`OPEN`)
- Are DOA claim emails sent? (`OPEN` — notification-service not in PLAN.md service list)
