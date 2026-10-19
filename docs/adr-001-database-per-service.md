# ADR-001: One database per service

**Status:** ACCEPTED (LOCKED in PLAN.md)  
**Date:** 2026-10-18  
**Linked:** [`HLD`](hld.md), [`DATA-OWNERSHIP`](data-ownership.md), [`PLAN.md`](../PLAN.md)

## Context
The aquarium fish shop platform is decomposed into independent microservices (users, catalog, inventory, orders, payments, gateway, storefront). Each service needs persistent storage for its domain entities (users, products with aquarium attributes, inventory reservations with DOA tracking, orders with state machine, payment transactions).

## Decision
Each service owns exactly one database. No cross-service tables, no shared schemas. SQLite for local development; PostgreSQL for production.

## Rationale
- Schema isolation prevents accidental coupling between services
- Each service can migrate independently (e.g., catalog adds aquarium attributes without affecting orders)
- Clear data ownership boundary matches service boundaries
- SQLite is sufficient for local dev/single-writer prototype; PostgreSQL handles production concurrency (orders, inventory reservations for perishable livestock, payment workflows)

## Consequences
**Positive:** Independent deployments, clear ownership, no distributed transactions across service DBs
**Negative:** Cross-service queries require API calls, not SQL joins; data consistency relies on events + compensating transactions
**Neutral:** SQLite file per service in dev; PostgreSQL instance per service in prod

## Open questions
- Production: one PostgreSQL instance with multiple databases, or one instance per service? (`OPEN`)
