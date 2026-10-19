# Requirements Traceability Matrix

**Document ID:** TRACE-001  
**Status:** DRAFT  
**Linked:** [`BRD`](brd.md), [`PRD`](prd.md), [`SRS`](srs.md), [`USER-STORIES`](user-stories.md), [`USE-CASES`](use-cases.md), [`HLD`](hld.md), [`DATA-OWNERSHIP`](data-ownership.md), [`API-CONTRACTS`](api-contracts.md), [`EVENTS`](events.md), [`TEST-STRATEGY`](test-strategy.md), [`SECURITY`](security.md), [`PLAN.md`](../PLAN.md)

## 1. Business requirement → Product requirement → Software requirement

| BR ID | BR description | PR ID | PR description | REQ ID | REQ description | Status |
|---|---|---|---|---|---|---|
| BR-001 | Customer registration & authentication | PR-001 | Customer registration & login | REQ-001 | User registration & authentication | CONFIRMED |
| BR-002 | Product catalog browsing | PR-002 | Product catalog | REQ-002 | Aquarium product catalog | CONFIRMED |
| BR-003 | Order placement | PR-003 | Order placement with inventory reservation | REQ-003 | Order creation | CONFIRMED |
| BR-004 | Inventory reserved before payment | PR-003 | Order placement with inventory reservation | REQ-005 | Inventory reservation | CONFIRMED |
| BR-005 | Payment success ≠ order confirmed | PR-003 | Order placement with inventory reservation | REQ-006 | Order confirmation | CONFIRMED |
| BR-006 | Failed steps compensated | PR-003 | Order placement with inventory reservation | REQ-007 | Order cancellation & compensation | CONFIRMED |
| BR-007 | At-least-once event delivery | PR-004 | Reliable event processing | REQ-008 | Event reliability | CONFIRMED |
| BR-008 | Dead-letter stream | PR-004 | Reliable event processing | REQ-008 | Event reliability | CONFIRMED |
| BR-009 | No card data storage | PR-005 | Secure payments | REQ-009 | Payment security | CONFIRMED |
| BR-010 | Webhook signature verification | PR-005 | Secure payments | REQ-009 | Payment security | CONFIRMED |
| BR-011 | Per-service authorization | PR-006 | Security & observability | REQ-010 | Authorization | CONFIRMED |
| BR-012 | Audit logging | PR-006 | Security & observability | REQ-011 | Audit logging | CONFIRMED |
| BR-013 | DOA claim handling | PR-007 | Livestock DOA guarantee | REQ-012 | DOA claim handling | CONFIRMED |
| BR-014 | Product attributes (water type, care level, etc.) | PR-002 | Product catalog | REQ-002 | Aquarium product catalog | CONFIRMED |

## 2. Software requirement → User story → Use case → Test case

| REQ ID | US ID | UC ID | TC ID | Status |
|---|---|---|---|---|
| REQ-001 | US-001, US-002 | UC-001, UC-002 | TC-001, TC-002, TC-003, TC-004 | CONFIRMED |
| REQ-002 | US-003 | UC-003 | TC-005 | CONFIRMED |
| REQ-003 | US-004, US-005 | UC-004 | TC-006, TC-007 | CONFIRMED |
| REQ-004 | US-005, US-006 | UC-005 | TC-007, TC-008 | CONFIRMED |
| REQ-005 | US-006 | UC-006 | TC-009, TC-010 | CONFIRMED |
| REQ-006 | US-007, US-008 | UC-007, UC-008 | TC-011, TC-012, TC-013, TC-014 | CONFIRMED |
| REQ-007 | US-008 | UC-008 | TC-012, TC-013, TC-014 | CONFIRMED |
| REQ-008 | US-005, US-006 | UC-005, UC-006 | TC-013, TC-014 | CONFIRMED |
| REQ-009 | US-006 | UC-005 | TC-008, TC-015 | CONFIRMED |
| REQ-010 | US-001–US-009 | All | TC-001–TC-016 | CONFIRMED |
| REQ-011 | — | — | TC-009, TC-016 | CONFIRMED |
| REQ-012 | US-009 | UC-009 | TC-016b | CONFIRMED |

## 3. User story → Acceptance criteria → Test case

| US ID | AC ID | TC ID | Status |
|---|---|---|---|
| US-001 | AC-001, AC-002 | TC-001, TC-002 | CONFIRMED |
| US-002 | AC-003, AC-004 | TC-003, TC-004 | CONFIRMED |
| US-003 | AC-005 | TC-005 | CONFIRMED |
| US-004 | AC-006, AC-007 | TC-006, TC-007 | CONFIRMED |
| US-005 | AC-008, AC-009 | TC-007, TC-008 | CONFIRMED |
| US-006 | AC-010, AC-011 | TC-009, TC-010 | CONFIRMED |
| US-007 | AC-012, AC-013 | TC-011, TC-013 | CONFIRMED |
| US-008 | AC-014, AC-015 | TC-012, TC-013, TC-014, TC-015 | CONFIRMED |
| US-009 | AC-016 | TC-016b | CONFIRMED |

## 4. Architecture decision → Linked requirements

| ADR ID | ADR title | Linked REQ IDs | Status |
|---|---|---|---|
| ADR-001 | One database per service | REQ-001 through REQ-012 (data isolation) | LOCKED |
| ADR-002 | Redis Streams for async events | REQ-008 | LOCKED |
| ADR-003 | Saga with compensating transactions | REQ-003, REQ-006, REQ-007 | LOCKED |
| ADR-004 | Payment sandbox; no card data | REQ-009 | LOCKED |
| ADR-005 | Gateway identity; per-service authZ | REQ-010 | LOCKED |

## 5. Open requirement gaps (documented explicitly)

| Gap | Description | Impact |
|---|---|---|
| STOREFRONT FRAMEWORK | React selected (`DECIDED`) | UI implementation can proceed |
| PAYMENT PROVIDER | Stripe sandbox (`DECIDED`) | Payments integration can proceed |
| DOA CLAIM WINDOW | 3 days or 7 days not decided | DOA claim validation logic deferred |
| JWT TTL | 60 minutes (`DECIDED`) | Auth security defined |
| PRODUCTION TARGET | Docker Compose on single VM (`DECIDED`) | Deployment strategy defined |
