"""Redis Streams publisher helper."""

import json
from typing import Any

import redis.asyncio as redis


class StreamPublisher:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def publish(self, stream: str, message: dict[str, Any]) -> str:
        fields = {k: (json.dumps(v) if not isinstance(v, (str, int, float)) else str(v))
                  for k, v in message.items()}
        return await self.redis.xadd(stream, fields)