"""Redis Streams consumer helpers - consumer groups, XACK, idempotency, XPENDING, DLQ."""

import json

import redis.asyncio as redis


class StreamConsumer:
    def __init__(self, redis_client: redis.Redis, stream: str, group: str, consumer: str):
        self.redis = redis_client
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self._seen: set[str] = set()

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except redis.ResponseError:
            # Group already exists
            pass

    async def is_duplicate(self, idempotency_key: str) -> bool:
        if idempotency_key in self._seen:
            return True
        self._seen.add(idempotency_key)
        return False

    async def read_messages(self, count: int = 10, block_ms: int = 5000):
        await self.ensure_group()
        messages = await self.redis.xreadgroup(
            self.group, self.consumer, {self.stream: ">"}, count=count, block=block_ms
        )
        return messages

    async def ack(self, message_id: str) -> None:
        await self.redis.xack(self.stream, self.group, message_id)

    async def claim_pending(self, min_idle_ms: int = 60000, count: int = 10):
        """Replay claimed messages from XPENDING after crash/restart."""
        pending = await self.redis.xpending(self.stream, self.group, min=min_idle_ms, count=count)
        if not pending:
            return []
        ids = [p["message_id"] for p in pending]
        messages = await self.redis.xclaim(
            self.stream, self.group, self.consumer, min_idle_time=min_idle_ms, message_ids=ids
        )
        return messages

    async def move_to_dlq(self, stream: str, message_id: str, message: dict, reason: str) -> None:
        dlq_stream = f"{stream}-dlq"
        entry = {
            "original_stream": stream,
            "original_id": message_id,
            "reason": reason,
            "message": json.dumps(message),
        }
        await self.redis.xadd(dlq_stream, entry)