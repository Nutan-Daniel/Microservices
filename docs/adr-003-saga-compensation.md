# ADR-003: Saga pattern with compensating transactions

**Status:** ACCEPTED (LOCKED in PLAN.md)  
**Date:** 2026-10-18  
**Linked:** [`HLD`](hld.md), [`SRS`](srs.md), [`PLAN.md`](../PLAN.md)

## Context
Order placement spans multiple services (orders → payments → inventory). No distributed transaction coordinator is available. A failure mid-saga must leave the system consistent, especially for perishable aquarium livestock where inventory accuracy is critical.

## Decision
Use a choreographed saga orchestrated by the orders service. Each step publishes an event; the next service acts and publishes a result. On any failure, compensating transactions run in reverse order (refund payment → release stock → cancel order). All compensations are idempotent.

## Rationale
- Avoids distributed transactions / 2PC across service databases
- Matches "one database per service" ownership rule
- Compensating transactions provide eventual consistency without a coordinator
- Order state machine (pending → reserved → confirmed → cancelled) makes progress visible
- Payment success does not automatically confirm an order — inventory reserve is a prerequisite (critical for perishable livestock)

## Consequences
**Positive:** No distributed lock coordinator; each service autonomous; failure recovery is explicit
**Negative:** Eventual consistency (orders may be temporarily inconsistent); complexity in compensation logic; partial failures must be handled
**Neutral:** Payment success does not automatically confirm an order — inventory reserve is a prerequisite

## Open questions
- Who triggers compensation if the orders service crashes mid-saga? (`OPEN` — pending-message recovery via XPENDING handles restart, but long-running saga state needs tracking)
