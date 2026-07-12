"""Параметризованные тесты изоляции тенантов (фабрик).

Проверяют контрактные границы: гостевой токен не может обращаться
к ресурсам другой фабрики.  Тесты работают на чистых функциях —
без Redis, HTTP, БД.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from api.access_control import has_factory_access
from api.guest_access import (
    CapabilityToken,
    GuestScope,
    decode_capability_token,
    encode_capability_token,
)

# ── Фикстуры ───────────────────────────────────────────────────────

@pytest.fixture
def factory_a() -> UUID:
    return uuid4()


@pytest.fixture
def factory_b() -> UUID:
    return uuid4()


@pytest.fixture
def secret() -> str:
    return "tenant-isolation-test-secret"


# ── Данные для параметризации ───────────────────────────────────────

SCOPE_CASES = [
    pytest.param(
        [GuestScope.READ_ORDER],
        id="read-order",
    ),
    pytest.param(
        [GuestScope.READ_BOM],
        id="read-bom",
    ),
    pytest.param(
        [GuestScope.READ_ORDER, GuestScope.READ_BOM],
        id="both-scopes",
    ),
    pytest.param(
        [GuestScope.WILDCARD],
        id="wildcard",
    ),
]


# ── Тесты контракта: same-factory ──────────────────────────────────

class TestSameFactoryAccess:
    """Гостевой токен + ресурс той же фабрики = доступ."""

    @pytest.mark.parametrize("scopes", SCOPE_CASES)
    def test_guest_token_same_factory_has_access(
        self,
        scopes: list[GuestScope],
        factory_a: UUID,
        secret: str,
    ) -> None:
        """Гость с токеном фабрики A получает доступ к ресурсу фабрики A."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=scopes,
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret)
        decoded = decode_capability_token(token_str, secret)
        assert decoded is not None

        # Контрактная проверка через access_control
        assert has_factory_access(
            resource_factory_id=factory_a,
            user_factory_id=decoded.factory_id,
        ) is True

    @pytest.mark.parametrize("scopes", SCOPE_CASES)
    def test_guest_token_same_factory_scopes_preserved(
        self,
        scopes: list[GuestScope],
        factory_a: UUID,
        secret: str,
    ) -> None:
        """Все scopes сохраняются при кодировании/декодировании."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=scopes,
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret)
        decoded = decode_capability_token(token_str, secret)
        assert decoded is not None
        assert decoded.scopes == scopes


# ── Тесты контракта: cross-factory ─────────────────────────────────

class TestCrossFactoryDenial:
    """Гостевой токен фабрики A НЕ даёт доступ к ресурсу фабрики B."""

    @pytest.mark.parametrize("scopes", SCOPE_CASES)
    def test_guest_token_cross_factory_denied(
        self,
        scopes: list[GuestScope],
        factory_a: UUID,
        factory_b: UUID,
        secret: str,
    ) -> None:
        """Токен фабрики A → ресурс фабрики B → 403."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=scopes,
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret)
        decoded = decode_capability_token(token_str, secret)
        assert decoded is not None

        # Контрактная проверка: другой factory_id → нет доступа
        assert has_factory_access(
            resource_factory_id=factory_b,
            user_factory_id=decoded.factory_id,
        ) is False

    @pytest.mark.parametrize(
        "requestor_scopes,target_factory",
        [
            ([GuestScope.READ_ORDER], "foreign"),
            ([GuestScope.READ_BOM], "foreign"),
            ([GuestScope.WILDCARD], "foreign"),
        ],
        ids=[
            "read-order→foreign",
            "read-bom→foreign",
            "wildcard→foreign",
        ],
    )
    def test_wildcard_does_not_bypass_tenant_boundary(
        self,
        requestor_scopes: list[GuestScope],
        target_factory: str,
        factory_a: UUID,
        factory_b: UUID,
        secret: str,
    ) -> None:
        """Wildcard scope НЕ обходит границу тенанта."""
        payload = CapabilityToken(
            factory_id=factory_a,
            scopes=requestor_scopes,
            expires_at="2099-01-01T00:00:00Z",
        )
        token_str = encode_capability_token(payload, secret)
        decoded = decode_capability_token(token_str, secret)
        assert decoded is not None

        # Даже с WILDCARD, cross-factory = denied
        assert has_factory_access(
            resource_factory_id=factory_b,
            user_factory_id=decoded.factory_id,
        ) is False


# ── Тесты: no token / anonymous ────────────────────────────────────

class TestAnonymousAccess:
    """Анонимный пользователь не получает доступ к приватным ресурсам."""

    @pytest.mark.parametrize(
        "resource_factory",
        [pytest.param(True, id="private-resource")],
    )
    def test_no_token_denied_for_private_resource(
        self,
        resource_factory: bool,
        factory_a: UUID,
    ) -> None:
        """Без токена (user_factory_id=None) → нет доступа к приватному ресурсу."""
        assert has_factory_access(
            resource_factory_id=factory_a if resource_factory else None,
            user_factory_id=None,
        ) is (not resource_factory)

    def test_anonymous_accessible_to_public_resource(self) -> None:
        """Анонимный доступ к публичному ресурсу (factory_id=None) разрешён."""
        assert has_factory_access(
            resource_factory_id=None,
            user_factory_id=None,
        ) is True
