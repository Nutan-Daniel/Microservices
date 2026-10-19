# Documentation Index and Project Glossary

## Purpose
This document is the entry point to the aquarium fish shop microservices documentation baseline. It defines where each document lives, the stable identifier scheme used across the documentation set, and the shared glossary of terms.

**Authoritative documents:**
- [`PLAN.md`](../PLAN.md) — implementation execution tracker (locked decisions, task list, validation steps)
- [`README.md`](../README.md) — project overview and repository layout

## Document map

| # | Document | File | Purpose |
|---|----------|------|---------|
| 1 | Documentation index & glossary | `docs/index.md` | This document |
| 2 | Business Requirements Document | `docs/brd.md` | Business goals, stakeholders, success criteria |
| 3 | Product Requirements Document | `docs/prd.md` | Product scope, features, user value |
| 4 | User personas, journeys, use cases, stories | `docs/personas.md`, `docs/user-journeys.md`, `docs/use-cases.md`, `docs/user-stories.md` | Who uses the system and what they need |
| 5 | Software Requirements Specification | `docs/srs.md` | Functional and non-functional requirements |
| 6 | High-Level Design | `docs/hld.md` | Architecture, service boundaries, data flow |
| 7 | Initial LLD (users service) | `docs/lld-users.md` | Detailed design for first service |
| 8 | Architecture Decision Records | `docs/adr-*.md` | Significant architectural decisions with context |
| 9 | API contracts & event specs | `docs/api-contracts.md`, `docs/events.md` | HTTP endpoints and Redis Streams events |
| 10 | Data ownership, models, migrations, consistency | `docs/data-ownership.md` | Per-service data, schema strategy, consistency |
| 11 | Test strategy, plan, quality gates | `docs/test-strategy.md` | Testing approach, automation, gates |
| 12 | Security requirements & threat model | `docs/security.md` | AuthN, authZ, secrets, threats, mitigations |
| 13 | Dev environment & coding standards | `docs/dev-standards.md` | Tooling, conventions, Ponytail principles |
| 14 | Deployment, observability, backup, recovery, ops | `docs/operations.md` | Runtime operations runbooks |
| 15 | CI/CD, release, rollback strategy | `docs/cicd.md` | Pipeline, release, rollback |
| 16 | Requirements traceability matrix | `docs/traceability.md` | Requirements → stories → designs → tests |
| 17 | Documentation review checklist | `docs/review-checklist.md` | Review criteria for all docs |

## Stable identifier scheme

| Identifier type | Prefix | Example | Used in |
|---|---|---|---|
| Business requirement | `BR-###` | `BR-001` | `docs/brd.md` |
| Product requirement | `PR-###` | `PR-001` | `docs/prd.md` |
| Software requirement | `REQ-###` | `REQ-001` | `docs/srs.md` |
| User story | `US-###` | `US-001` | `docs/user-stories.md` |
| Use case | `UC-###` | `UC-001` | `docs/use-cases.md` |
| Architecture decision | `ADR-###` | `ADR-001` | `docs/adr-*.md` |
| Acceptance criterion | `AC-###` | `AC-001` | `docs/user-stories.md`, `docs/srs.md` |
| Test case | `TC-###` | `TC-001` | `docs/test-strategy.md` |
| Threat | `THR-###` | `THR-001` | `docs/security.md` |

## Glossary

| Term | Definition |
|---|---|
| Service | An independently deployable Python/FastAPI microservice owning its database and exposing HTTP + Redis Streams interfaces. |
| API Gateway | FastAPI service that routes client requests to downstream services; clients call the gateway only, never services directly. |
| Storefront | Dedicated React frontend application that consumes the gateway API. |
| Order | A customer purchase request, tracked through a state machine: `pending` → `reserved` → `confirmed` (or `cancelled`). |
| State machine | The order lifecycle: `pending` → payment initiated → inventory reserved → payment captured → `confirmed`. Failure at any step compensates back to `cancelled`. |
| Compensating transaction | A reverse action that undoes a completed step when a later step fails (e.g., refund payment, release stock, cancel order). |
| Saga | A sequence of local transactions coordinated by the orders service, with compensating transactions for failure recovery. |
| Outbox | Transactional outbox pattern: events are written to an outbox table in the same DB transaction as the state change, then relayed to Redis Streams. |
| Consumer group | Redis Streams consumer group providing at-least-once delivery with explicit `XACK` after processing. |
| Idempotency key | A deterministic key (e.g., `orderId`) checked by every async consumer before mutating state, so duplicate deliveries are no-ops. |
| XPENDING | Redis Streams pending entries list; consumers replay claimed messages from here after crash/restart. |
| Bounded retries | N delivery attempts per message (N=3); messages exceeding the bound move to a dead-letter stream. |
| Dead-letter stream (DLQ) | Dedicated Redis Stream for messages that exceed retry bounds; retained for inspection and replay, never silently dropped. |
| Webhook signature verification | Cryptographic verification of payment-provider callbacks to confirm authenticity. |
| Defense in depth | Identity centralized at the gateway, but authorization enforced independently in each service. |
| Secrets management | Environment variables / Docker secrets; no secrets committed to git. |
| At-least-once delivery | A message may be delivered more than once; consumers must be idempotent. |
| Exactly-once processing | Not guaranteed by Redis Streams alone; achieved via idempotent handlers + transactional outbox + deduplication keys. |
| Livestock | Live animals (fish, corals, invertebrates, aquatic plants) sold through the shop; perishable, require climate-aware shipping. |
| WYSIWYG | "What You See Is What You Get" — unique specimen (e.g., specific coral colony) shown in photo; once sold, item is removed from inventory. |
| Water type | Classification of aquatic environment: freshwater, saltwater, or both. |
| DOA (Dead on Arrival) | Livestock that arrives dead; covered by guarantee with photo evidence within a time window. |
| Care level | Difficulty of keeping a species: beginner, intermediate, or advanced. |
| Compatibility | Whether species can coexist in the same tank (temperament, size, water parameters). |

## Decision status legend

| Label | Meaning |
|---|---|
| `LOCKED` | Decision made in PLAN.md; do not change without explicit approval. |
| `CONFIRMED` | Decision made in this documentation set; stable. |
| `ASSUMPTION` | Working assumption pending validation. |
| `OPEN` | Unresolved question; must be answered before implementation of the affected area. |
| `RECOMMENDATION` | Suggested direction; not yet locked. |

## Open decisions (as of baseline)
- DOA claim window: 3 days or 7 days? (`OPEN`)
- Production monitoring/alerting stack (`OPEN`)
- Storefront implementation details (`IN PROGRESS` — React selected)
