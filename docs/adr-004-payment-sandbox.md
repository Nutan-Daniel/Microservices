# ADR-004: Payment sandbox; no card data storage

**Status:** ACCEPTED (LOCKED in PLAN.md)  
**Date:** 2026-10-18  
**Linked:** [`HLD`](hld.md), [`SRS`](srs.md), [`SECURITY`](security.md), [`PLAN.md`](../PLAN.md)

## Context
The payments service must integrate with a payment provider without exposing the platform to PCI DSS scope for card data handling.

## Decision
Use a payment-provider sandbox (Stripe) initially. Never store card numbers or CVVs. Store only provider reference/token. Verify provider webhook signatures on every callback. Handle duplicate callbacks idempotently.

## Rationale
- Stripe sandbox avoids real money during development
- Not storing card numbers/CVVs eliminates primary PCI DSS scope
- Webhook signature verification prevents spoofed callbacks
- Idempotent duplicate handling prevents double charges from retried callbacks

## Consequences
**Positive:** Minimal compliance burden; safe development environment; no sensitive card data at rest
**Negative:** Sandbox behavior may differ from production provider; must re-verify against production API before go-live
**Neutral:** Provider token/reference stored instead of PAN; token can be revoked via provider API

## Open questions
- Webhook retry policy from provider? (`OPEN` — Stripe default retries; handle idempotently)
