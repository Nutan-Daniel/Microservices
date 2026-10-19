# Deployment, Observability, Backup, Recovery, and Operations Runbooks

**Document ID:** OPS-001  
**Status:** DRAFT  
**Locked:** Docker Compose deployment (from PLAN.md)  
**Linked:** [`HLD`](hld.md), [`DATA-OWNERSHIP`](data-ownership.md), [`SECURITY`](security.md), [`PLAN.md`](../PLAN.md)

**Ponytail note:** Minimal viable operations. Docker Compose is the specified deployment target. Production target is undefined (`OPEN`). Do not over-engineer runbooks for infrastructure that doesn't exist yet.

## 1. Local deployment (Docker Compose)

| Command | Purpose |
|---|---|
| `docker compose up -d` | Start all services + Redis + storefront |
| `docker compose down` | Stop and remove containers |
| `docker compose config --quiet` | Validate compose file |
| `docker compose logs -f <service>` | View service logs |

**Health check:** `curl http://localhost:8000/health` returns 200 when gateway is up.

## 2. Observability

| Concern | Approach | Status |
|---|---|---|
| Health endpoint | `GET /health` on gateway; service-level health per service | PLAN.md task 11 |
| Logging | Structured logs; auth events, order state changes, payment events, DOA claims | SEC-009 |
| Metrics | Not specified for MVP (`OPEN`) | — |
| Tracing | Not specified for MVP (`OPEN`) | — |
| Log aggregation | Not specified for MVP (`OPEN`) | — |

## 3. Backup and recovery

| Asset | Backup approach | Recovery |
|---|---|---|
| SQLite DB files (dev) | File copy / volume snapshot | Restore file; restart service |
| PostgreSQL DBs (prod) | `pg_dump` per service DB | `pg_restore` per service DB |
| Redis Streams | Not durable by default; AOF (`appendonly yes` in compose) | Redis restart with AOF replay |
| Outbox table | Part of service DB backup | Replay unpublished outbox events |

**Recovery procedure:** Restore DB → restart service → outbox relay publishes unpublished events → consumers replay `XPENDING`.

## 4. Operations runbooks

### Runbook OPS-01: Service unhealthy
1. `docker compose logs <service>` — inspect recent errors
2. `docker compose restart <service>` — restart the service
3. Verify `curl <service-health>` returns 200
4. If persistent, check DB connectivity and Redis connectivity

### Runbook OPS-02: Order stuck mid-saga
1. Check orders DB for orders in `pending` or `reserved` without recent transitions
2. Check Redis `XPENDING` for unacknowledged messages in consumer groups
3. Reclaim pending messages; consumers reprocess idempotently
4. Verify order reaches `confirmed` or `cancelled`

### Runbook OPS-03: Dead-letter stream has entries
1. `XRANGE <domain>-dlq - +` — inspect DLQ entries
2. Identify failure reason from entry metadata
3. Fix root cause (code, config, dependency)
4. Replay message manually or purge after review

### Runbook OPS-04: Payment webhook duplicate
1. Verify idempotency key dedup prevented duplicate charge (TC-009)
2. If duplicate occurred, refund via `/payments/refund`
3. Investigate provider retry configuration

### Runbook OPS-05: Secret suspected leaked
1. Rotate the secret (JWT_SECRET_KEY, WEBHOOK_SECRET, provider keys)
2. Update environment variables / Docker secrets
3. Restart affected services
4. Audit git history for committed secrets (`git log -p --all | grep -i secret`)

### Runbook OPS-06: DOA claim processing
1. Check inventory DB for `doa_reported` reservations without compensation
2. Verify refund or replacement was processed in payments/orders
3. Mark order as `refunded` or `replacement_shipped`

## 5. Open questions
- Production deployment target (Docker Compose is dev; prod undefined) (`DECIDED`: Docker Compose on single VM)
- Log retention period? (`OPEN`)
- Backup schedule? (`OPEN`)
- Monitoring/alerting stack (Prometheus/Grafana)? (`OPEN` — not in MVP scope)
