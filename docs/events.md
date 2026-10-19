# Redis Streams Event Specifications

**Document ID:** EVT-001  
**Status:** DRAFT  
**Linked:** [`HLD`](hld.md), [`USE-CASES`](use-cases.md), [`ADR-002`](adr-002-redis-streams.md), [`PLAN.md`](../PLAN.md)

## Convention
- Stream name format: `<domain>-events`
- Consumer group format: `<consumer-service>-group`
- Idempotency key: deterministic `orderId` or `eventId` in message body
- Delivery: at-least-once; consumers `XACK` after successful processing
- Recovery: replay `XPENDING` after crash/restart
- Retries: N=3 attempts, then dead-letter stream `<domain>-dlq`

## Event catalog

| Event | Stream | Producer | Consumer group(s) | Idempotency key |
|---|---|---|---|---|
| user.created | user-events | users | users-group | userId |
| user.updated | user-events | users | users-group | userId |
| product.created | catalog-events | catalog | catalog-group | productId |
| product.updated | catalog-events | catalog | catalog-group | productId |
| stock.changed | catalog-events | catalog | inventory-group | productId |
| stock.reserved | inventory-events | inventory | orders-group | reservationId |
| stock.released | inventory-events | inventory | orders-group | reservationId |
| stock.decremented | inventory-events | inventory | orders-group | reservationId |
| stock.doa_reported | inventory-events | inventory | orders-group | reservationId |
| order.created | order-events | orders | payments-group | orderId |
| order.paid | order-events | orders | inventory-group | orderId |
| order.cancelled | order-events | orders | payments-group, inventory-group | orderId |
| order.doa_claim | order-events | orders | payments-group | orderId |
| payment.succeeded | payment-events | payments | orders-group | paymentId |
| payment.failed | payment-events | payments | orders-group | paymentId |
| payment.refunded | payment-events | payments | orders-group | paymentId |

## Event schema (example)

```json
{
  "eventId": "uuid-v4",
  "eventType": "order.created",
  "aggregateType": "order",
  "aggregateId": "order-123",
  "idempotencyKey": "order-123",
  "payload": { ... },
  "timestamp": "2026-10-18T12:00:00Z",
  "correlationId": "uuid-v4",
  "causationId": "uuid-v4"
}
```

## Consumer behavior (per service)

| Behavior | Implementation |
|---|---|
| Read from stream | `XREADGROUP` with consumer group |
| Process message | Check idempotency key first; if seen, `XACK` and skip |
| Mutate state | In local DB transaction |
| Publish outbound events | Via transactional outbox (same DB transaction) |
| Acknowledge | `XACK` after successful processing + outbox write |
| Crash/restart | Reclaim `XPENDING` entries; reprocess idempotently |
| Exceed retry bound (N=3) | Move to `<domain>-dlq` stream |

## Dead-letter stream

| Field | Value |
|---|---|
| Stream | `<domain>-dlq` (e.g., `order-dlq`) |
| Entry format | Original message + failure reason + retry count + timestamp |
| Retention | Indefinite (manual inspection/replay) |
| Alerting | New DLQ entry triggers review (`OPEN` — alerting not yet specified) |

## Order of operations (saga for aquarium order)

1. orders → `order.created` (order-events)
2. payments consumes → charges sandbox → `payment.succeeded` / `payment.failed` (payment-events)
3. orders consumes `payment.succeeded` → inventory reserve stock → `stock.reserved` / release (inventory-events)
4. orders consumes `stock.reserved` → capture payment → order `confirmed`
5. On any failure → compensating actions → `order.cancelled` (order-events)
6. DOA flow: customer reports DOA → `stock.doa_reported` → order marked `doa_claimed` → compensation (refund/replacement)

## Open questions
- Consumer group name convention finalization (`RECOMMENDATION`: `<consumer-service>-group`)
- DLQ alerting mechanism (`OPEN`)
