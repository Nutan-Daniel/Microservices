"""Transactional outbox relay - writes events to outbox table, publishes to Redis Streams."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.events import EventEnvelope


class OutboxRelay:
    def __init__(self, session: AsyncSession, redis_publisher):
        self.session = session
        self.redis_publisher = redis_publisher

    async def publish(self, event_type: str, aggregate_type: str, aggregate_id: str,
                      idempotency_key: str, payload: dict[str, Any],
                      correlation_id: str | None = None,
                      causation_id: str | None = None) -> None:
        envelope = EventEnvelope(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=idempotency_key,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        # Insert into outbox table in same transaction as state change
        await self.session.execute(
            "INSERT INTO outbox (aggregate_type, aggregate_id, event_type, payload) "
            "VALUES (:aggregate_type, :aggregate_id, :event_type, :payload)",
            {
                "aggregate_type": envelope.aggregate_type,
                "aggregate_id": envelope.aggregate_id,
                "event_type": envelope.event_type,
                "payload": envelope.model_dump_json(),
            },
        )
        # Publish to Redis Streams
        await self.redis_publisher.publish(
            stream=f"{envelope.aggregate_type}-events",
            message=envelope.model_dump(),
        )