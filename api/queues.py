from __future__ import annotations

import json
from typing import Any, Awaitable, cast

import redis.asyncio as aioredis
from redis.asyncio import Redis as AsyncRedis

from .settings import settings


DXF_QUEUE = "cam:dxf"
GCODE_QUEUE = "cam:gcode"
ZIP_QUEUE = "cam:zip"
DLQ_QUEUE = "cam:dlq"


def get_redis() -> AsyncRedis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


import uuid

async def enqueue(queue: str, payload: dict[str, Any]) -> int:
    r = get_redis()
    payload["idempotency_key"] = str(uuid.uuid4())
    return await cast(Awaitable[int], r.lpush(queue, json.dumps(payload)))


async def dequeue(queue: str) -> dict[str, Any] | None:
    r = get_redis()
    raw = await cast(Awaitable[str | None], r.rpop(queue))
    return json.loads(raw) if raw else None
