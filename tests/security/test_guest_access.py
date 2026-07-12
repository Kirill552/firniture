"""Тесты гостевого capability-токена и изоляции по фабрикам.

TDD: сначала падающий тест, потом реализация.
Контрактные тесты — на чистых функциях без Redis/HTTP.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from api.guest_access import (
    CapabilityToken,
    GuestScope,
    decode_capability_token,
    encode_capability_token,
    extract_factory_id_from_token,
    has_scope,
    is_expired,
)

# ── Фикстуры ───────────────────────────────────────────────────────

@pytest.fixture
def factory_a() -> UUID:
    """Первая тестовая фабрика."""
    return uuid4()


@pytest.fixture
def factory_b() -> UUID:
    """Вторая тестовая фабрика (чужая)."""
    return uuid4()


@pytest.fixture
def secret_key() -> str:
    """Секрет для подписи токенов в тестах."""
    return "test-secret-key-not-production"


# ── Кодирование / декодирование ────────────────────────────────────

class TestEncodeDecode:
    """Круговой тест кодирования."""

    def test_roundtrip(self, factory_a: UUID, secret_key: str) -> None:
        """Токен кодируется и декодируется без потерь."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret_key)
        decoded = decode_capability_token(token_str, secret_key)
        assert decoded is not None
        assert decoded.factory_id == factory_a
        assert decoded.scopes == [GuestScope.READ_ORDER]

    def test_returns_none_on_wrong_secret(self, factory_a: UUID) -> None:
        """Неверный ключ подписи — токен невалиден."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, "secret-a")
        decoded = decode_capability_token(token_str, "secret-b")
        assert decoded is None

    def test_returns_none_on_tampered_token(self, factory_a: UUID, secret_key: str) -> None:
        """Подменённое содержимое — токен невалиден."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret_key)
        # Подменяем один байт в base64-части (не в подписи)
        parts = token_str.rsplit(".", 1)
        corrupted_body = parts[0][:-1] + ("A" if parts[0][-1] != "A" else "B")
        tampered = corrupted_body + "." + parts[1]
        decoded = decode_capability_token(tampered, secret_key)
        assert decoded is None

    def test_returns_none_on_empty_string(self, secret_key: str) -> None:
        """Пустая строка — токен невалиден."""
        assert decode_capability_token("", secret_key) is None

    def test_returns_none_on_garbage(self, secret_key: str) -> None:
        """Мусор — токен невалиден."""
        assert decode_capability_token("not-a-valid-token", secret_key) is None


# ── Проверка истечения ─────────────────────────────────────────────

class TestIsExpired:
    """Проверка TTL токена."""

    def test_not_expired_future(self, factory_a: UUID, secret_key: str) -> None:
        """Токен с будущим expiration — не истёк."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret_key)
        assert is_expired(token_str, secret_key) is False

    def test_expired_past(self, factory_a: UUID, secret_key: str) -> None:
        """Токен с прошлым expiration — истёк."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2000-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret_key)
        assert is_expired(token_str, secret_key) is True


# ── Scopes ──────────────────────────────────────────────────────────

class TestScopes:
    """Проверка ограничений областей доступа."""

    def test_has_scope_positive(self) -> None:
        """Scope присутствует в списке."""
        assert has_scope([GuestScope.READ_ORDER], GuestScope.READ_ORDER) is True

    def test_has_scope_negative(self) -> None:
        """Scope отсутствует в списке."""
        assert has_scope([GuestScope.READ_ORDER], GuestScope.READ_BOM) is False

    def test_empty_scopes_grants_nothing(self) -> None:
        """Пустой список scopes — ничего не разрешено."""
        assert has_scope([], GuestScope.READ_ORDER) is False

    def test_wildcard_matches_any(self) -> None:
        """Wildcard scope разрешает всё."""
        assert has_scope([GuestScope.WILDCARD], GuestScope.READ_ORDER) is True
        assert has_scope([GuestScope.WILDCARD], GuestScope.READ_BOM) is True

    def test_extract_factory_id(self, factory_a: UUID, secret_key: str) -> None:
        """Извлечение factory_id из токена без полной проверки подписи."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret_key)
        extracted = extract_factory_id_from_token(token_str)
        assert extracted == factory_a


# ── Изоляция фабрик (same/cross) ───────────────────────────────────

@pytest.mark.parametrize(
    "same_factory,expected",
    [
        (True, True),
        (False, False),
    ],
    ids=["same-factory-allows", "cross-factory-denies"],
)
class TestFactoryIsolation:
    """Гостевой токен привязан к фабрике-владельцу."""

    def test_isolation(
        self,
        same_factory: bool,
        expected: bool,
        factory_a: UUID,
        factory_b: UUID,
        secret_key: str,
    ) -> None:
        """
        Токен выдан фабрикой A.
        same_factory=True → проверяем доступ от имени фабрики A → ok.
        same_factory=False → проверяем доступ от имени фабрики B → denied.
        """
        token_owner = factory_a
        requestor = factory_a if same_factory else factory_b

        payload = CapabilityToken(
            factory_id=token_owner,
            scopes=[GuestScope.READ_ORDER],
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret_key)
        decoded = decode_capability_token(token_str, secret_key)
        assert decoded is not None

        # Контрактная проверка: токен принадлежит фабрике requestor?
        has_access = decoded.factory_id == requestor
        assert has_access is expected

import asyncio

from api.rate_limits import InMemoryRateLimiter, RateLimitRule

# ── Rate Limiter ───────────────────────────────────────────────────

class TestInMemoryRateLimiter:
    """Проверка InMemoryRateLimiter: Retry-After семантика."""

    @pytest.fixture
    def limiter(self) -> InMemoryRateLimiter:
        return InMemoryRateLimiter()

    def test_allows_under_limit(self, limiter: InMemoryRateLimiter) -> None:
        """Запрос в пределах лимита — allowed."""
        rule = RateLimitRule(max_requests=5, window_seconds=60)
        result = asyncio.get_event_loop().run_until_complete(
            limiter.check("ip:127.0.0.1", rule)
        )
        assert result.allowed is True
        assert result.remaining == 4
        assert result.retry_after is None

    def test_blocks_over_limit(self, limiter: InMemoryRateLimiter) -> None:
        """Запрос сверх лимита — denied с Retry-After."""
        rule = RateLimitRule(max_requests=2, window_seconds=60)
        key = "ip:10.0.0.1"
        asyncio.get_event_loop().run_until_complete(limiter.check(key, rule))
        asyncio.get_event_loop().run_until_complete(limiter.check(key, rule))
        result = asyncio.get_event_loop().run_until_complete(
            limiter.check(key, rule)
        )
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_per_key_isolation(self, limiter: InMemoryRateLimiter) -> None:
        """Каждый ключ имеет свой счётчик."""
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        r1 = asyncio.get_event_loop().run_until_complete(limiter.check("a", rule))
        r2 = asyncio.get_event_loop().run_until_complete(limiter.check("b", rule))
        assert r1.allowed is True
        assert r2.allowed is True  # другой ключ — свой лимит

    def test_reset_clears_counter(self, limiter: InMemoryRateLimiter) -> None:
        """reset() сбрасывает счётчик."""
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        key = "ip:192.168.1.1"
        asyncio.get_event_loop().run_until_complete(limiter.check(key, rule))
        blocked = asyncio.get_event_loop().run_until_complete(
            limiter.check(key, rule)
        )
        assert blocked.allowed is False

        asyncio.get_event_loop().run_until_complete(limiter.reset(key))
        allowed = asyncio.get_event_loop().run_until_complete(
            limiter.check(key, rule)
        )
        assert allowed.allowed is True

    def test_rule_validation(self) -> None:
        """Невалидные правила — ValueError."""
        with pytest.raises(ValueError, match="max_requests"):
            RateLimitRule(max_requests=0, window_seconds=60)
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimitRule(max_requests=5, window_seconds=0)

    def test_retry_after_not_exceeds_window(self, limiter: InMemoryRateLimiter) -> None:
        """Retry-After никогда не превышает window_seconds."""
        rule = RateLimitRule(max_requests=1, window_seconds=10)
        key = "ip:172.16.0.1"
        asyncio.get_event_loop().run_until_complete(limiter.check(key, rule))
        result = asyncio.get_event_loop().run_until_complete(
            limiter.check(key, rule)
        )
        assert result.retry_after is not None
        assert result.retry_after <= rule.window_seconds