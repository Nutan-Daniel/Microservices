# CI/CD, Release, and Rollback Strategy

**Document ID:** CI-CD-001  
**Status:** DRAFT  
**Locked:** Automated dependency/security scans in CI (from PLAN.md)  
**Linked:** [`TEST-STRATEGY`](test-strategy.md), [`SECURITY`](security.md), [`PLAN.md`](../PLAN.md)

**Ponytail note:** Minimal viable CI. Run lint, tests, SAST, and dependency scan on every change. Release/rollback are manual for MVP; automate only when release frequency justifies it.

## 1. CI pipeline (per change / pull request)

| Stage | Tool | Command | Gate |
|---|---|---|---|
| Lint | ruff | `python -m ruff check .` | Must pass |
| Format | ruff | `python -m ruff format --check .` | Must pass |
| Tests | pytest | `python -m pytest` | Must pass |
| SAST | bandit | `python -m bandit -r gateway users catalog inventory orders payments shared` | No high/medium |
| Dependency scan | pip-audit | `python -m pip_audit` | No vulnerable packages |
| Compose validate | docker compose | `docker compose config --quiet` | Exit 0 |

## 2. Release strategy

| Aspect | Approach |
|---|---|
| Release trigger | Manual tag on main branch |
| Versioning | SemVer (e.g., `v0.1.0`) |
| Build | Docker images per service via `docker compose build` |
| Deploy | `docker compose up -d` (local/dev); production target: Docker Compose on single VM (`DECIDED`) |
| Rollback | `docker compose up -d` with previous image tag; restore DB from backup |

## 3. Rollback procedure

| Step | Action |
|---|---|
| 1 | Identify last known-good image tag |
| 2 | `docker compose stop <affected-service>` |
| 3 | `docker compose up -d <affected-service>` with previous tag |
| 4 | If DB migration was applied, restore DB from pre-migration backup |
| 5 | Verify health endpoint; verify order state machine consistency |

## 4. What is NOT automated (MVP)
- Canary deployments (`OPEN`)
- Blue-green deployments (`OPEN`)
- Automated rollback on test failure (`OPEN`)
- Production Kubernetes (`OPEN` — Docker Compose is the target)

## 5. Open questions
- CI platform: GitHub Actions (`DECIDED`)
- Container registry: ghcr.io (`DECIDED`)
- Automated release notes generation? (`OPEN`)
