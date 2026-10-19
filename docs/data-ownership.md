# Data Ownership, Data Model, Migration, and Consistency Strategy

**Document ID:** DATA-001  
**Status:** DRAFT  
**Locked:** One database per service (from PLAN.md)  
**Linked:** [`HLD`](hld.md), [`ADR-001`](adr-001-database-per-service.md), [`SRS`](srs.md), [`PLAN.md`](../PLAN.md)

## 1. Data ownership (locked from PLAN.md)

| Service | Database (dev) | Database (prod) | Owns |
|---|---|---|---|
| users | users.db | users PostgreSQL DB | users, auth, profiles |
| catalog | catalog.db | catalog PostgreSQL DB | products, categories, stock snapshot (with aquarium attributes) |
| inventory | inventory.db | inventory PostgreSQL DB | stock reservations/decrements, livestock tracking, DOA reporting |
| orders | orders.db | orders PostgreSQL DB | orders, order items, state machine, DOA claims |
| payments | payments.db | payments PostgreSQL DB | payment transactions |
| gateway | none | none | routing only (no data) |
| storefront | none | none | UI layer (no data) |

**Rule:** No cross-service tables, no shared schemas. Cross-service reads happen via HTTP API calls, never direct DB access.

## 2. Per-service data models

### Users service (users.db)
- `users` table: id, email, password_hash, created_at, updated_at
- `outbox` table: id, aggregate_type, aggregate_id, event_type, payload, created_at, published_at

### Catalog service (catalog.db)
- `products` table: id, name, description, price, category_id, product_type, water_type, is_wysiwyg, is_livestock, species, scientific_name, care_level, max_size_cm, temperament, temp_min_c, temp_max_c, ph_min, ph_max, diet, origin, compatibility_notes, brand, tank_size_min_litres, power_watts, created_at, updated_at
- `categories` table: id, name, description, created_at
- `stock_snapshot` table: product_id, available_quantity, updated_at (read-only mirror for fast lookup)
- `outbox` table

### Inventory service (inventory.db)
- `stock_reservations` table: id, product_id, quantity, status (reserved/released/decremented/doa_reported), order_id, reason, is_livestock, doa_reported, doa_reported_at, doa_evidence_url, created_at, updated_at
- `outbox` table

### Orders service (orders.db)
- `orders` table: id, user_id, status (pending/reserved/confirmed/cancelled/doa_claimed), total, created_at, updated_at
- `order_items` table: id, order_id, product_id, quantity, price
- `outbox` table

### Payments service (payments.db)
- `payment_transactions` table: id, order_id, amount, status (succeeded/failed/refunded), provider_reference, idempotency_key, created_at, updated_at
- `outbox` table

## 3. Migration strategy

| Aspect | Approach |
|---|---|
| Migration tool | Alembic (per service, own migrations directory) |
| Dev | SQLite; `alembic upgrade head` on service start |
| Prod | PostgreSQL; `alembic upgrade head` as deployment step |
| Backward compatibility | Additive-only changes during deploy; breaking changes require two-phase deploy |
| Outbox table | Included in each service's migrations |

## 4. Consistency strategy

| Consistency type | Mechanism |
|---|---|
| Within a service | ACID transaction (single DB per service) |
| Across services | Eventual consistency via Redis Streams + transactional outbox |
| Order lifecycle | Saga with compensating transactions (ADR-003) |
| Event delivery | At-least-once (consumer groups + `XACK`); exactly-once processing via idempotency keys |
| Idempotency | `orderId`/`eventId` dedup key checked before every state mutation |
| Duplicate handling | Idempotent consumers; duplicate webhook callbacks produce no duplicate charges |
| Recovery | `XPENDING` replay after crash/restart; dead-letter stream for exceeded retries |

## 5. Consistency trade-offs (documented explicitly)

| Trade-off | Decision | Impact |
|---|---|---|
| Strong vs eventual consistency | Eventual across services | Orders may be briefly inconsistent mid-saga; state machine makes progress visible |
| Availability vs consistency | Availability prioritized | Services remain available during partial outages; sagas resume on recovery |
| Exactly-once delivery | Not guaranteed by Redis Streams alone | Achieved via idempotency + outbox; added complexity in consumers |
| Perishable livestock | Reservations have implicit expiry | Livestock reservations should be confirmed quickly; DOA window applies after delivery |

## 6. Open questions
- Stock snapshot vs live inventory read: catalog stores stock snapshot; inventory owns reservations. How are they kept in sync? (`OPEN` — stock.changed event from inventory to catalog)
- Alembic migration storage: per-service directory or shared migrations repo? (`RECOMMENDATION`: per-service directory under each service)
- DOA claim window: 3 days or 7 days? (`OPEN`)
