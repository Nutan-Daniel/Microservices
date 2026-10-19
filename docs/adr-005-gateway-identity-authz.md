# ADR-005: Gateway centralizes identity; per-service authorization

**Status:** ACCEPTED (LOCKED in PLAN.md)  
**Date:** 2026-10-18  
**Linked:** [`HLD`](hld.md), [`SRS`](srs.md), [`SECURITY`](security.md), [`PLAN.md`](../PLAN.md)

## Context
Clients call the gateway only. Authentication can be centralized, but authorization must not depend solely on the gateway (defense in depth).

## Decision
Centralize identity/authentication at the gateway (JWT validation, user context injection). Each service independently enforces authorization for its own resources. Never trust the gateway alone.

## Rationale
- Single auth entry point simplifies client integration
- Per-service authorization prevents a compromised gateway from bypassing access control
- Matches defense-in-depth principle

## Consequences
**Positive:** Centralized token validation; defense in depth; service autonomy
**Negative:** JWT must be forwarded to downstream services; each service must implement authZ logic
**Neutral:** Services trust gateway-validated JWT but re-check permissions locally

## Open questions
- How is user context propagated to downstream services? (JWT header forwarding) (`RECOMMENDATION`: forward Authorization header)
