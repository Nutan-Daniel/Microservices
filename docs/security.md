# Security Requirements and Initial Threat Model

**Document ID:** SEC-001  
**Status:** DRAFT  
**Linked:** [`SRS`](srs.md), [`HLD`](hld.md), [`ADR-004`](adr-004-payment-sandbox.md), [`ADR-005`](adr-005-gateway-identity-authz.md), [`TEST-STRATEGY`](test-strategy.md), [`PLAN.md`](../PLAN.md)

## 1. Security requirements

| ID | Requirement | Description | Priority | Status | Linked |
|---|---|---|---|---|---|
| SEC-001 | No card data storage | Never store card numbers or CVVs | Must | CONFIRMED | ADR-004, REQ-009 |
| SEC-002 | Provider tokens only | Store only payment-provider reference/token | Must | CONFIRMED | ADR-004 |
| SEC-003 | Webhook signature verification | Verify every payment-provider callback signature | Must | CONFIRMED | ADR-004, REQ-009 |
| SEC-004 | Duplicate callback idempotency | Same payment intent processed once | Must | CONFIRMED | ADR-004, REQ-009 |
| SEC-005 | Centralized identity | Gateway validates JWT, injects user context | Must | CONFIRMED | ADR-005, REQ-010 |
| SEC-006 | Per-service authorization | Each service enforces its own authZ (defense in depth) | Must | CONFIRMED | ADR-005, REQ-010 |
| SEC-007 | Rate limiting | At gateway and per-service | Should | CONFIRMED | REQ-011 |
| SEC-008 | Secrets management | Env vars / Docker secrets; never committed | Must | CONFIRMED | REQ-012 |
| SEC-009 | Audit logging | Auth events, order state changes, payment events, DOA claims | Should | CONFIRMED | REQ-011 |
| SEC-010 | Dependency scanning | Automated pip-audit in CI | Should | CONFIRMED | REQ-014 |
| SEC-011 | SAST scanning | Automated bandit in CI | Should | CONFIRMED | REQ-014 |

## 2. Threat model

| Threat ID | Threat | Asset | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|---|
| THR-001 | Card data exfiltration from DB | Payment data | Low | Critical | Never store card/CVV; store provider token only | CONFIRMED |
| THR-002 | Spoofed payment webhook | Payments service | Medium | High | Verify provider webhook signature on every callback | CONFIRMED |
| THR-003 | Duplicate charge from retried callback | Payments service | Medium | High | Idempotency key dedup on payment intent | CONFIRMED |
| THR-004 | Unauthorized access via stolen JWT | All services | Medium | High | Short-lived tokens (60 min); per-service authZ; gateway validates | CONFIRMED |
| THR-005 | Secrets committed to git | All services | Low | Critical | Env vars / Docker secrets; `.gitignore` excludes `.env`; pre-commit scan | CONFIRMED |
| THR-006 | Rate abuse / brute force | Gateway, users | Medium | Medium | Rate limiting at gateway and per-service | CONFIRMED |
| THR-007 | Compromised gateway bypasses authZ | All services | Low | High | Per-service authorization (defense in depth) | CONFIRMED |
| THR-008 | Vulnerable dependency | All services | Medium | Medium | pip-audit in CI; keep deps patched | CONFIRMED |
| THR-009 | Injection via API input | All services | Medium | High | Input validation; parameterized queries (SQLAlchemy) | CONFIRMED |
| THR-010 | Event replay / duplicate processing | All async consumers | Medium | Medium | Idempotency keys; `XACK` after processing | CONFIRMED |
| THR-011 | Fraudulent DOA claim | Inventory/orders | Medium | Medium | Require photo evidence; validate reservation is livestock; time window | CONFIRMED |
| THR-012 | Livestock inventory inaccuracy | Inventory service | Medium | High | Real-time stock updates; reservation before payment; DOA tracking | CONFIRMED |

## 3. Security controls by layer

| Layer | Controls |
|---|---|
| Gateway | JWT validation, rate limiting, user context injection, request routing |
| Users | Password hashing (pbkdf2_hmac stdlib), JWT issuance, input validation |
| Catalog | Read-only product access; authZ on mutating endpoints; aquarium attribute validation |
| Inventory | Stock reservation authZ; service-to-service JWT; DOA claim validation |
| Orders | State machine validation; compensation authZ; DOA claim processing |
| Payments | Webhook signature verification; idempotency; no card storage; sandbox provider |
| Storefront | No secrets; calls gateway only; CSRF protection (`OPEN` — not yet specified) |

## 4. Secrets management

| Secret | Source | Never committed? |
|---|---|---|
| JWT_SECRET_KEY | Environment variable / Docker secret | Yes |
| WEBHOOK_SECRET | Environment variable / Docker secret | Yes |
| Payment provider keys | Environment variable / Docker secret | Yes |
| Database credentials | Environment variable / Docker secret | Yes |

## 5. Audit logging events

| Event | Logged by |
|---|---|
| User registration | users service |
| User login (success/failure) | users service |
| Order state change | orders service |
| Payment success/failure | payments service |
| Authorization denial | each service |
| Stock reserve/release | inventory service |
| DOA claim filed | inventory service |

## 6. Open questions
- JWT access token TTL: 60 minutes (`DECIDED`)
- Refresh token rotation? (`OPEN`)
- Storefront CSRF protection mechanism? (`OPEN`)
- Production secret store (e.g., Vault, AWS Secrets Manager) vs env vars? (`OPEN`)
- DOA claim evidence retention period? (`OPEN`)
