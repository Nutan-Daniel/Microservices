# ADR-002: Redis Streams for async events

**Status:** ACCEPTED (LOCKED in PLAN.md)  
**Date:** 2026-10-18  
**Linked:** [`HLD`](hld.md), [`EVENTS`](events.md), [`PLAN.md`](../PLAN.md)

## Context
Services need to coordinate asynchronously (order → payment → inventory for aquarium livestock). The mechanism must provide reliable delivery and recovery after crashes, especially for perishable livestock where order state must be accurate.

## Decision
Use Redis Streams with consumer groups for async event delivery. Add transactional outbox, idempotent handlers, XPENDING recovery, bounded retries (N=3), and a dead-letter stream.

## Rationale
- Redis Streams consumer groups provide at-least-once delivery with explicit `XACK`
- Lightweight, already in the stack (Redis is the async broker)
- XPENDING enables pending-message recovery after restart
- Outbox pattern ensures atomicity: state change + event in same DB transaction
- Bounded retries (N=3) prevent poison messages from blocking the saga

## Consequences
**Positive:** Simple operational footprint; built-in consumer groups; pending-message recovery
**Negative:** Consumer groups provide delivery mechanics, not exactly-once processing — requires idempotent handlers + deduplication keys
**Neutral:** Dead-letter stream retained for inspection; messages never silently dropped

## Open questions
- None (retry bound decided: N = 3)
