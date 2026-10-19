# Business Requirements Document (BRD)

**Document ID:** BRD-001  
**Status:** DRAFT  
**Linked:** [`PRD`](prd.md), [`SRS`](srs.md), [`PLAN.md`](../PLAN.md)

## 1. Business objective
Build a greenfield aquarium fish shop platform that allows customers to browse and purchase freshwater and saltwater fish, corals, invertebrates, aquatic plants, and aquarium equipment, with reliable inventory reservation, live animal guarantees, and climate-aware shipping.

## 2. Stakeholders

| Stakeholder | Role | Interest |
|---|---|---|
| Customer (hobbyist) | End user | Browse fish/equipment, place orders, pay, view order status, file DOA claims |
| Business owner | Product/operations | Revenue capture, accurate livestock inventory, DOA claim management |
| Platform engineer | Operations | Deployable, observable, secure services |
| Security reviewer | Compliance | No card data stored, webhook verification, audit logging |

## 3. Business requirements

| ID | Requirement | Priority | Status | Linked PRD |
|---|---|---|---|---|
| BR-001 | Customers can register and authenticate | High | CONFIRMED | PR-001 |
| BR-002 | Customers can browse aquarium products (fish, corals, equipment, supplies) | High | CONFIRMED | PR-002 |
| BR-003 | Customers can place an order for in-stock products | High | CONFIRMED | PR-003 |
| BR-004 | Inventory is reserved before payment is captured | High | CONFIRMED | PR-003 |
| BR-005 | A successful payment does not automatically confirm an order | High | CONFIRMED | PR-003 |
| BR-006 | Failed steps are compensated (stock released, payment refunded, order cancelled) | High | CONFIRMED | PR-003 |
| BR-007 | Events are delivered at least once with idempotent handling | High | CONFIRMED | PR-004 |
| BR-008 | Messages exceeding retry bounds go to a dead-letter stream | Medium | CONFIRMED | PR-004 |
| BR-009 | Card numbers and CVVs are never stored | High | CONFIRMED | PR-005 |
| BR-010 | Payment provider webhooks are signature-verified | High | CONFIRMED | PR-005 |
| BR-011 | Authorization is enforced in each service (defense in depth) | High | CONFIRMED | PR-006 |
| BR-012 | Audit logging records auth, state changes, payment events, DOA claims | Medium | CONFIRMED | PR-006 |
| BR-013 | Livestock can be marked as DOA (Dead on Arrival) with evidence | High | CONFIRMED | PR-007 |
| BR-014 | Products carry aquarium attributes (water type, care level, species, etc.) | High | CONFIRMED | PR-002 |

## 4. Success criteria (measurable)

| ID | Criterion | Target | Measurement |
|---|---|---|---|
| SC-001 | Order creation succeeds when product is in stock | ≥99% success rate | E2E test pass rate |
| SC-002 | Failed payment results in order cancellation within 30s | ≤30s | End-to-end timing test |
| SC-003 | Duplicate payment webhook does not create duplicate charge | 0 duplicate charges | Idempotency test |
| SC-004 | Message exceeding retry bound reaches DLQ | 100% of exceeded messages | DLQ inspection |
| SC-005 | No card numbers or CVVs in any service database | 0 occurrences | Database scan + bandit |
| SC-006 | DOA claim with evidence updates reservation status | 100% of valid claims | DOA claim test |

## 5. Out of scope (explicitly not in this release)
- Multi-currency support
- Subscription / recurring payments
- Physical shipping carrier integration (climate-aware shipping logic only)
- Multi-tenant seller marketplace
- Production Kubernetes deployment (Docker Compose is the deployment target per PLAN.md)

## 6. Open questions
- Which payment-provider sandbox will be integrated first? (`OPEN`)
- What is the exact retry bound N for bounded retries? (`DECIDED`: N = 3)
- DOA claim window: 3 days or 7 days? (`OPEN`)
