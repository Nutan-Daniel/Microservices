# Product Requirements Document (PRD)

**Document ID:** PRD-001  
**Status:** DRAFT  
**Linked:** [`BRD`](brd.md), [`SRS`](srs.md), [`USER-STORIES`](user-stories.md), [`USE-CASES`](use-cases.md), [`PLAN.md`](../PLAN.md)

## 1. Product vision
A reliable aquarium fish shop where customers can browse freshwater and saltwater fish, corals, invertebrates, aquatic plants, and aquarium equipment, with confidence that inventory is reserved before payment is captured, and that livestock arrives healthy or is covered by a DOA guarantee.

## 2. Product requirements

| ID | Requirement | Description | Priority | Status | Linked BRD | Linked user stories |
|---|---|---|---|---|---|---|
| PR-001 | Customer registration & login | Customers can create an account and sign in | High | CONFIRMED | BR-001 | US-001, US-002 |
| PR-002 | Product catalog | Customers can browse aquarium products (fish, corals, equipment, supplies) with species/water type attributes | High | CONFIRMED | BR-002, BR-014 | US-003 |
| PR-003 | Order placement with inventory reservation | Order created in `pending`, inventory reserved before payment captured | High | CONFIRMED | BR-003, BR-004, BR-005, BR-006 | US-004, US-005, US-006, US-007, US-008 |
| PR-004 | Reliable event processing | At-least-once delivery, idempotent handlers, bounded retries, dead-letter stream | High | CONFIRMED | BR-007, BR-008 | US-005, US-006 |
| PR-005 | Secure payments | Sandbox provider, no card/CVV storage, webhook verification, duplicate callback handling | High | CONFIRMED | BR-009, BR-010 | US-006 |
| PR-006 | Security & observability | Per-service authorization, rate limiting, secrets management, audit logging | High | CONFIRMED | BR-011, BR-012 | US-001, US-005, US-006 |
| PR-007 | Livestock DOA guarantee | Customers can report Dead on Arrival with evidence; claims processed with compensation | High | CONFIRMED | BR-013 | US-008 |
| PR-008 | Storefront UI | Dedicated React frontend consuming the gateway API | Medium | CONFIRMED | — | US-003 through US-007 |

## 3. User value propositions
- Customers can trust that an order is only confirmed after inventory is reserved and payment is captured.
- Livestock orders are covered by a DOA guarantee — dead specimens are exchanged or refunded.
- Product catalog includes detailed species attributes (care level, water parameters, compatibility) to help customers make informed choices.
- Failed orders are automatically rolled back (stock released, payment refunded) so customers are not charged for undeliverable items.

## 4. Non-goals (out of scope for MVP)
- Guest checkout (account required per PR-001)
- Order tracking / shipping integration (carrier integration)
- Product reviews and ratings
- Discount codes and coupons
- Multi-region deployment
- Fish breeding / trading marketplace

## 5. Assumptions
- Customers have an email address for registration.
- Payment provider sandbox (Stripe) is available during development.
- Docker Desktop is available for local development.
- Livestock shipping uses climate-aware packaging (business rule, not system integration).

## 6. Open questions
- Storefront framework: React selected (`DECIDED`)
- DOA claim window: 3 days or 7 days? (`OPEN`)
