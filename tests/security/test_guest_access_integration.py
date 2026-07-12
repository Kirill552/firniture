"""Интеграционные тесты guest/auth capabilities.

Контракт:
- Signed expiring capability token → guest order access
- Claim-after-login: factory binding enforcement
- Reject missing secret, UUID-only fallback
- Same/cross factory, expiry, scope tests
- Injected dependencies/fakes only — no browser, no live Redis.

TDD: Red → Green → Refactor.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from api.access_control import (
    GuestIdentity,
    claim_factory_access,
    claim_guest_order_access,
    enforce_access,
    guest_has_scope,
    resolve_guest_identity,
    resolve_guest_identity_strict,
    validate_guest_order_access,
)
from api.guest_access import (
    CapabilityToken,
    GuestScope,
    encode_capability_token,
)

# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def factory_a() -> UUID:
    return uuid4()


@pytest.fixture
def factory_b() -> UUID:
    return uuid4()


@pytest.fixture
def secret() -> str:
    return "integration-test-secret-key"


@pytest.fixture
def user_a_id() -> UUID:
    return uuid4()


@pytest.fixture
def user_b_id() -> UUID:
    return uuid4()


def _make_token(
    factory_id: UUID,
    scopes: list[GuestScope] | None = None,
    expires_at: str = "2099-01-01T00:00:00Z",
    secret: str = "test-secret",
) -> str:
    """Хелпер: кодирует capability-токен с заданными параметрами."""
    payload = CapabilityToken(
        factory_id=factory_id,
        scopes=scopes or [GuestScope.READ_ORDER],
        expires_at=expires_at,
    )
    return encode_capability_token(payload, secret)


def _expired_token(factory_id: UUID, secret: str) -> str:
    """Хелпер: кодирует токен, истёкший 1 час назад."""
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    return _make_token(factory_id, expires_at=past, secret=secret)


# ── Same-factory guest order access ────────────────────────────────


class TestSameFactoryAccess:
    """Guest token bound to factory A → access to order of factory A."""

    def test_validate_order_access_same_factory(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, [GuestScope.READ_ORDER], secret=secret)
        identity = validate_guest_order_access(
            token_str=token_str,
            secret=secret,
            order_factory_id=factory_a,
            required_scope=GuestScope.READ_ORDER,
        )
        assert identity.factory_id == factory_a
        assert GuestScope.READ_ORDER in identity.scopes

    def test_validate_order_access_wildcard_scope(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, [GuestScope.WILDCARD], secret=secret)
        identity = validate_guest_order_access(
            token_str=token_str,
            secret=secret,
            order_factory_id=factory_a,
            required_scope=GuestScope.READ_BOM,
        )
        assert identity.factory_id == factory_a

    def test_validate_order_access_read_bom_scope(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, [GuestScope.READ_BOM], secret=secret)
        identity = validate_guest_order_access(
            token_str=token_str,
            secret=secret,
            order_factory_id=factory_a,
            required_scope=GuestScope.READ_BOM,
        )
        assert GuestScope.READ_BOM in identity.scopes

    def test_resolve_identity_same_factory(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        identity = resolve_guest_identity(token_str, secret)
        assert identity is not None
        assert identity.factory_id == factory_a


# ── Cross-factory denial ───────────────────────────────────────────


class TestCrossFactoryDenial:
    """Guest token for factory A → denied access to order of factory B."""

    def test_validate_order_cross_factory_denied(
        self,
        factory_a: UUID,
        factory_b: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        with pytest.raises(Exception, match="does not match order factory"):
            validate_guest_order_access(
                token_str=token_str,
                secret=secret,
                order_factory_id=factory_b,
            )

    def test_enforce_access_cross_factory(
        self,
        factory_a: UUID,
        factory_b: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        identity = resolve_guest_identity(token_str, secret)
        assert identity is not None
        with pytest.raises(Exception, match="Нет доступа к ресурсу"):
            enforce_access(
                resource_factory_id=factory_b,
                identity=identity,
                required_scope=GuestScope.READ_ORDER,
            )

    def test_wildcard_does_not_bypass_tenant_boundary(
        self,
        factory_a: UUID,
        factory_b: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, [GuestScope.WILDCARD], secret=secret)
        identity = resolve_guest_identity(token_str, secret)
        assert identity is not None
        with pytest.raises(Exception, match="Нет доступа к ресурсу"):
            enforce_access(
                resource_factory_id=factory_b,
                identity=identity,
            )

    def test_claim_cross_factory_denied(
        self,
        factory_a: UUID,
        factory_b: UUID,
        user_a_id: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        with pytest.raises(Exception, match="does not match user factory"):
            claim_guest_order_access(
                token_str=token_str,
                secret=secret,
                user_factory_id=factory_b,
            )


# ── Expiry enforcement ─────────────────────────────────────────────


class TestExpiryEnforcement:
    """Expired tokens are rejected at every validation point."""

    def test_validate_order_expired_denied(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _expired_token(factory_a, secret)
        with pytest.raises(Exception, match="expired"):
            validate_guest_order_access(
                token_str=token_str,
                secret=secret,
                order_factory_id=factory_a,
            )

    def test_resolve_identity_expired_returns_none(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _expired_token(factory_a, secret)
        identity = resolve_guest_identity(token_str, secret)
        assert identity is None

    def test_claim_expired_denied(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _expired_token(factory_a, secret)
        with pytest.raises(Exception, match="expired"):
            claim_guest_order_access(
                token_str=token_str,
                secret=secret,
                user_factory_id=factory_a,
            )

    def test_valid_token_not_rejected_as_expired(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        identity = resolve_guest_identity(token_str, secret)
        assert identity is not None


# ── Missing secret rejection ───────────────────────────────────────


class TestMissingSecretRejection:
    """Empty/missing secret → fail closed at every point."""

    def test_resolve_identity_empty_secret(
        self,
        factory_a: UUID,
    ) -> None:
        token_str = _make_token(factory_a, secret="real-secret")
        identity = resolve_guest_identity(token_str, secret="")
        assert identity is None

    def test_validate_order_empty_secret(
        self,
        factory_a: UUID,
    ) -> None:
        token_str = _make_token(factory_a, secret="real-secret")
        with pytest.raises(Exception, match="not configured"):
            validate_guest_order_access(
                token_str=token_str,
                secret="",
                order_factory_id=factory_a,
            )

    def test_claim_empty_secret(
        self,
        factory_a: UUID,
    ) -> None:
        token_str = _make_token(factory_a, secret="real-secret")
        with pytest.raises(Exception, match="not configured"):
            claim_guest_order_access(
                token_str=token_str,
                secret="",
                user_factory_id=factory_a,
            )

    def test_strict_resolve_empty_secret(
        self,
        factory_a: UUID,
    ) -> None:
        token_str = _make_token(factory_a, secret="real-secret")
        identity = resolve_guest_identity_strict(token_str, secret="")
        assert identity is None


# ── UUID-only token rejection ──────────────────────────────────────


class TestUUIDOnlyTokenRejection:
    """Bare UUIDs must not be accepted as capability tokens."""

    def test_validate_order_uuid_only_denied(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        raw_uuid = str(uuid4())
        with pytest.raises(Exception, match="UUID-only"):
            validate_guest_order_access(
                token_str=raw_uuid,
                secret=secret,
                order_factory_id=factory_a,
            )

    def test_strict_resolve_uuid_only_raises(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        raw_uuid = str(uuid4())
        with pytest.raises(ValueError, match="UUID-only"):
            resolve_guest_identity_strict(raw_uuid, secret)

    def test_claim_uuid_only_denied(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        raw_uuid = str(uuid4())
        with pytest.raises(Exception, match="UUID-only"):
            claim_guest_order_access(
                token_str=raw_uuid,
                secret=secret,
                user_factory_id=factory_a,
            )

    def test_none_token_returns_none_not_uuid_fallback(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        identity = resolve_guest_identity(None, secret)
        assert identity is None


# ── Claim-after-login flow ─────────────────────────────────────────


class TestClaimAfterLogin:
    """Claim flow: guest logs in → presents capability token → factory binding checked."""

    def test_claim_same_factory_succeeds(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        identity = claim_guest_order_access(
            token_str=token_str,
            secret=secret,
            user_factory_id=factory_a,
        )
        assert identity.factory_id == factory_a

    def test_claim_cross_factory_fails(
        self,
        factory_a: UUID,
        factory_b: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret=secret)
        with pytest.raises(Exception, match="does not match user factory"):
            claim_guest_order_access(
                token_str=token_str,
                secret=secret,
                user_factory_id=factory_b,
            )

    def test_claim_expired_token_fails(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _expired_token(factory_a, secret)
        with pytest.raises(Exception, match="expired"):
            claim_guest_order_access(
                token_str=token_str,
                secret=secret,
                user_factory_id=factory_a,
            )

    def test_claim_preserves_scopes(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        scopes = [GuestScope.READ_ORDER, GuestScope.READ_BOM]
        token_str = _make_token(factory_a, scopes, secret=secret)
        identity = claim_guest_order_access(
            token_str=token_str,
            secret=secret,
            user_factory_id=factory_a,
        )
        assert identity.scopes == scopes

    def test_claim_factory_access_same(
        self,
        factory_a: UUID,
    ) -> None:
        """claim_factory_access (legacy) passes on same factory."""
        claim_factory_access(factory_a, factory_a)  # No exception = pass

    def test_claim_factory_access_cross_fails(
        self,
        factory_a: UUID,
        factory_b: UUID,
    ) -> None:
        """claim_factory_access (legacy) raises on cross factory."""
        with pytest.raises(Exception, match="не совпадает"):
            claim_factory_access(factory_a, factory_b)


# ── Scope enforcement ──────────────────────────────────────────────


class TestScopeEnforcement:
    """Scopes are enforced at every validation point."""

    def test_order_access_requires_read_order(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(
            factory_a,
            [GuestScope.READ_BOM],  # Has READ_BOM, not READ_ORDER
            secret=secret,
        )
        with pytest.raises(Exception, match="scope"):
            validate_guest_order_access(
                token_str=token_str,
                secret=secret,
                order_factory_id=factory_a,
                required_scope=GuestScope.READ_ORDER,
            )

    def test_enforce_access_scope_denied(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(
            factory_a,
            [GuestScope.READ_ORDER],
            secret=secret,
        )
        identity = resolve_guest_identity(token_str, secret)
        assert identity is not None
        with pytest.raises(Exception, match="scope"):
            enforce_access(
                resource_factory_id=factory_a,
                identity=identity,
                required_scope=GuestScope.READ_BOM,
            )

    def test_wildcard_satisfies_any_scope(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, [GuestScope.WILDCARD], secret=secret)
        identity = validate_guest_order_access(
            token_str=token_str,
            secret=secret,
            order_factory_id=factory_a,
            required_scope=GuestScope.READ_BOM,
        )
        assert identity is not None

    def test_guest_has_scope_positive(self) -> None:
        ident = GuestIdentity(
            factory_id=uuid4(),
            scopes=[GuestScope.READ_ORDER],
            token_id="t1",
        )
        assert guest_has_scope(ident, GuestScope.READ_ORDER) is True

    def test_guest_has_scope_negative(self) -> None:
        ident = GuestIdentity(
            factory_id=uuid4(),
            scopes=[GuestScope.READ_ORDER],
            token_id="t1",
        )
        assert guest_has_scope(ident, GuestScope.READ_BOM) is False


# ── Token tampering ────────────────────────────────────────────────


class TestTokenTampering:
    """Tampered tokens are rejected."""

    def test_wrong_secret_rejected(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        token_str = _make_token(factory_a, secret="correct-secret")
        with pytest.raises(Exception, match="Invalid"):
            validate_guest_order_access(
                token_str=token_str,
                secret=secret,  # Different secret
                order_factory_id=factory_a,
            )

    def test_garbage_token_rejected(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        with pytest.raises(Exception, match="Invalid"):
            validate_guest_order_access(
                token_str="not-a-valid-token",
                secret=secret,
                order_factory_id=factory_a,
            )

    def test_empty_token_rejected(
        self,
        factory_a: UUID,
        secret: str,
    ) -> None:
        with pytest.raises(Exception, match="Требуется"):
            validate_guest_order_access(
                token_str="",
                secret=secret,
                order_factory_id=factory_a,
            )



# ── Route-level regression: resolve_guest_capability dependency ─────


class TestResolveGuestCapabilityRouteLevel:
    """
    Маршрутный уровень: resolve_guest_capability отвергает
    UUID-only/невалидный/истёкший токен через HTTP 401.
    """

    @pytest.fixture()
    def _app(self, secret: str):
        """Минимальное FastAPI-приложение с тестовым маршрутом через resolve_guest_capability."""
        from unittest.mock import patch

        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        import api.auth as _auth_module
        from api.auth import resolve_guest_capability

        app = FastAPI()

        @app.get("/test-guest")
        async def _test_endpoint(
            guest: GuestIdentity | None = Depends(resolve_guest_capability),
        ):
            if guest is None:
                return {"status": "anonymous"}
            return {"status": "guest", "factory_id": str(guest.factory_id)}

        # Патчим settings в модуле auth — туда импортирован объект settings
        with patch.object(_auth_module, "settings") as mock_settings:
            mock_settings.GUEST_CAPABILITY_SECRET = secret
            client = TestClient(app, raise_server_exceptions=False)
            yield client, secret

    def test_no_header_returns_anonymous(self, _app):
        """Отсутствие заголовка → 200 anonymous (dependency → None)."""
        client, _ = _app
        resp = client.get("/test-guest")
        assert resp.status_code == 200
        assert resp.json()["status"] == "anonymous"

    def test_valid_token_returns_guest(self, _app, factory_a):
        """Валидный capability-токен → 200 guest."""
        client, secret = _app
        token_str = _make_token(factory_a, secret=secret)
        resp = client.get(
            "/test-guest",
            headers={"X-Guest-Capability": token_str},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "guest"
        assert resp.json()["factory_id"] == str(factory_a)

    def test_uuid_only_token_returns_401(self, _app):
        """UUID-only токен → 401 (не проходит через dependency)."""
        client, _ = _app
        raw_uuid = str(uuid4())
        resp = client.get(
            "/test-guest",
            headers={"X-Guest-Capability": raw_uuid},
        )
        assert resp.status_code == 401
        assert "Невалидный" in resp.json()["detail"]

    def test_garbage_token_returns_401(self, _app):
        """Невалидный токен → 401."""
        client, _ = _app
        resp = client.get(
            "/test-guest",
            headers={"X-Guest-Capability": "not-a-valid-token"},
        )
        assert resp.status_code == 401
        assert "Невалидный" in resp.json()["detail"]

    def test_expired_token_returns_401(self, _app, factory_a):
        """Истёкший токен → 401."""
        client, secret = _app
        token_str = _expired_token(factory_a, secret)
        resp = client.get(
            "/test-guest",
            headers={"X-Guest-Capability": token_str},
        )
        assert resp.status_code == 401
        assert "Невалидный" in resp.json()["detail"]

    def test_tampered_wrong_secret_returns_401(self, _app, factory_a):
        """Подменённый токен (wrong secret) → 401."""
        client, secret = _app
        token_str = _make_token(factory_a, secret="wrong-secret")
        resp = client.get(
            "/test-guest",
            headers={"X-Guest-Capability": token_str},
        )
        assert resp.status_code == 401
        assert "Невалидный" in resp.json()["detail"]