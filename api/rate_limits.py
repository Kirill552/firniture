"""Абстракция Rate Limiter с Retry-After семантикой.

Интерфейс: `RateLimiter` (Protocol).
Реализации: `InMemoryRateLimiter` (тесты), `RedisRateLimiter` (прод).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

import redis.asyncio as aioredis

# ── Модели ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RateLimitResult:
    """Результат проверки rate limit."""
    allowed: bool
    remaining: int  # Оставшиеся запросы в текущем окне
    limit: int  # Максимум запросов в окне
    retry_after: float | None = None  # Секунды до следующего разрешённого запроса (None если allowed)


@dataclass
class RateLimitRule:
    """Правило ограничения: max запросов за window_seconds."""
    max_requests: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.max_requests <= 0:
            raise ValueError("max_requests должен быть > 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds должен быть > 0")


# ── Протокол ────────────────────────────────────────────────────────

class RateLimiter(Protocol):
    """Интерфейс rate limiter. Ключ — произвольная строка (IP, user_id, etc.)."""

    async def check(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """Проверить и зафиксировать запрос. Возвращает результат с Retry-After."""
        ...

    async def reset(self, key: str) -> None:
        """Сбросить счётчик для ключа."""
        ...


# ── In-memory (тесты) ──────────────────────────────────────────────

@dataclass
class _BucketState:
    """Состояние окна для одного ключа."""
    count: int = 0
    window_start: float = field(default_factory=time.monotonic)


class InMemoryRateLimiter:
    """In-memory rate limiter для тестов. Не thread-safe — ОК для single-thread pytest."""

    def __init__(self) -> None:
        self._buckets: dict[str, _BucketState] = {}

    async def check(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        now = time.monotonic()
        bucket = self._buckets.get(key)

        if bucket is None or (now - bucket.window_start) >= rule.window_seconds:
            # Новое окно
            bucket = _BucketState(count=1, window_start=now)
            self._buckets[key] = bucket
            return RateLimitResult(
                allowed=True,
                remaining=rule.max_requests - 1,
                limit=rule.max_requests,
            )

        bucket.count += 1
        if bucket.count <= rule.max_requests:
            return RateLimitResult(
                allowed=True,
                remaining=rule.max_requests - bucket.count,
                limit=rule.max_requests,
            )

        # Превышен лимит — вычисляем Retry-After
        retry_after = rule.window_seconds - (now - bucket.window_start)
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=rule.max_requests,
            retry_after=max(0.0, retry_after),
        )

    async def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


# ── Redis-backed (прод) ─────────────────────────────────────────────

class RedisRateLimiter:
    """Redis-backed rate limiter с sliding-window через sorted sets.

    Алгоритм:
    1. Удаляем просроченные записи (ZREMRANGEBYSCORE).
    2. Добавляем текущий запрос (ZADD).
    3. Считаем количество活跃ных записей (ZCARD).
    4. Если > max_requests → reject + Retry-After.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis_client

    def _key(self, key: str) -> str:
        return f"ratelimit:{key}"

    async def check(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        redis_key = self._key(key)
        now = time.time()
        window_start = now - rule.window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", window_start)  # type: ignore[union-attr]
        pipe.zadd(redis_key, {str(now): now})  # type: ignore[union-attr]
        pipe.zcard(redis_key)  # type: ignore[union-attr]
        pipe.expire(redis_key, rule.window_seconds)  # type: ignore[union-attr]
        results = await pipe.execute()  # type: ignore[union-attr]

        count = results[2]

        if count <= rule.max_requests:
            return RateLimitResult(
                allowed=True,
                remaining=rule.max_requests - count,
                limit=rule.max_requests,
            )

        # Превышен — вычисляем Retry-After: время до старейшей записи в окне
        oldest = await self._redis.zrange(redis_key, 0, 0, withscores=True)  # type: ignore[union-attr]
        if oldest:
            oldest_time = oldest[0][1]
            retry_after = rule.window_seconds - (now - oldest_time)
        else:
            retry_after = float(rule.window_seconds)

        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=rule.max_requests,
            retry_after=max(0.0, retry_after),
        )

    async def reset(self, key: str) -> None:
        await self._redis.delete(self._key(key))  # type: ignore[union-attr]


# ── Guest upload specific rate rules (Task 1) ────────────────────────
# Используются в guest_upload.py и routers.py; здесь находится единый источник настроек.
GUEST_BURST_RULE = RateLimitRule(max_requests=3, window_seconds=600)
GUEST_DAILY_RULE = RateLimitRule(max_requests=10, window_seconds=86400)
