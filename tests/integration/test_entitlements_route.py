"""Интеграционные тесты entitlements route — GET /api/v1/entitlements.

Проверяет:
- Регистрация роутера (explicit contract)
- Аутентификация required
- Cross-factory boundary: only own factory entitlements returned
- Response contract: capabilities dict, audit trail, grant snapshots
- 503 when persistence/provider integration is absent
- Engine evaluation: capabilities resolve correctly through route
- Audit-safe grant state: applied/rejected/disposition fields present
- No provider-specific code (Stripe, webhook и т.д.)

Ограничения:
- Не модифицирует api.entitlements, api.billing, api.routers, models, frontend.
- Все persistence-запросы мокаются через unittest.mock.patch.
- Нет browser, нет network.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.billing import GrantReason, ManualGrant, PlanTier
from api.entitlements import Capability
from api.models import User
from api.routes.entitlements import (
    FactoryBillingState,
    entitlements_router,
)

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

FACTORY_A = uuid.uuid4()
FACTORY_B = uuid.uuid4()
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID, factory_id: uuid.UUID) -> User:
    """Build a lightweight User mock (no DB session needed)."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.factory_id = factory_id
    return user


@pytest.fixture
def entitlements_app() -> FastAPI:
    """Create a test FastAPI app with the entitlements router mounted."""
    app = FastAPI()
    app.include_router(entitlements_router)
    return app


@pytest.fixture
def user_a() -> User:
    return _make_user(USER_A_ID, FACTORY_A)


@pytest.fixture
def user_b() -> User:
    return _make_user(USER_B_ID, FACTORY_B)


def _make_free_billing_state() -> FactoryBillingState:
    """Factory billing state for FREE tier, no grants."""
    return FactoryBillingState(tier=PlanTier.FREE, grants=[])


def _make_pro_billing_state_with_grants(
    grants: list[ManualGrant] | None = None,
) -> FactoryBillingState:
    """Factory billing state for PRO tier with optional grants."""
    return FactoryBillingState(
        tier=PlanTier.PRO,
        grants=grants or [],
    )


def _patch_billing(state: FactoryBillingState | None = None):
    """Context manager to patch _load_factory_billing_state.

    When state is None (default), persistence is absent → 503.
    When state is a FactoryBillingState, route resolves capabilities.
    """
    async def _loader(factory_id: str) -> FactoryBillingState | None:
        return state

    return patch(
        "api.routes.entitlements._load_factory_billing_state",
        side_effect=_loader,
    )


# ──────────────────────────────────────────────────────────────────────
# 1. Router registration contract
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsRouterRegistration:
    """Explicit registration contract — router is importable and has the right endpoint."""

    def test_router_exists_and_has_prefix(self) -> None:
        """Router is importable, has expected prefix."""
        assert entitlements_router.prefix == "/api/v1/entitlements"
        assert entitlements_router.tags == ["Entitlements"]

    def test_router_has_get_endpoint(self) -> None:
        """Router exposes GET /entitlements (root)."""
        routes = {r.path: r.methods for r in entitlements_router.routes}
        assert "/api/v1/entitlements" in routes
        assert "GET" in routes["/api/v1/entitlements"]

    def test_router_can_be_included(self, entitlements_app: FastAPI) -> None:
        """include_router works without error."""
        routes = {r.path for r in entitlements_app.routes}
        assert "/api/v1/entitlements" in routes

    def test_route_is_not_registered_in_main_app(self) -> None:
        """Entitlements router is NOT auto-registered in api.main.app.

        Registration must be explicit — this test documents the deferred
        registration contract. When ready, add:
            from api.routes.entitlements import entitlements_router
            app.include_router(entitlements_router)
        to api/main.py.
        """
        from api.main import app

        routes = {r.path for r in app.routes}
        assert "/api/v1/entitlements" not in routes


# ──────────────────────────────────────────────────────────────────────
# 2. Authentication required
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsAuthentication:
    """Unauthenticated requests are rejected."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, entitlements_app: FastAPI) -> None:
        """No auth header → 401 from get_current_user."""

        async def _no_auth():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        entitlements_app.dependency_overrides[get_current_user] = _no_auth

        transport = ASGITransport(app=entitlements_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/entitlements")
        assert resp.status_code in (401, 403)


# ──────────────────────────────────────────────────────────────────────
# 3. Persistence not available → 503
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsPersistenceMissing:
    """When persistence layer is absent, route returns clear 503."""

    @pytest.mark.asyncio
    async def test_no_persistence_returns_503(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """When billing state is None (default) → 503."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        # Patch _load_factory_billing_state to return None (default behavior)
        with _patch_billing(state=None):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        body = resp.json()
        assert "Billing persistence not integrated" in body["detail"]
        assert "FactoryBillingState" in body["detail"]

    @pytest.mark.asyncio
    async def test_503_detail_is_actionable(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """503 detail message tells developer exactly what to implement."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(state=None):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        detail = resp.json()["detail"]
        assert "_load_factory_billing_state" in detail
        assert "FactoryBillingState" in detail


# ──────────────────────────────────────────────────────────────────────
# 4. Response contract — capabilities returned correctly
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsResponseContract:
    """When persistence IS wired, route returns valid entitlements."""

    @pytest.mark.asyncio
    async def test_free_tier_returns_all_capabilities(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """FREE tier: all 6 capability keys present with correct values."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(_make_free_billing_state()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()

        # All required keys present
        expected_keys = {cap.value for cap in Capability}
        assert set(body["capabilities"].keys()) == expected_keys

        # FREE tier specific values
        assert body["capabilities"]["project_count"] == 1
        assert body["capabilities"]["ai_budget"] == 0
        assert body["capabilities"]["preview_export"] is True
        assert body["capabilities"]["production_export"] is False
        assert body["capabilities"]["certified_profiles"] == 1
        assert body["capabilities"]["team_seats"] == 1

    @pytest.mark.asyncio
    async def test_factory_id_matches_authenticated_user(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Returned factory_id matches the authenticated user's factory."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(_make_free_billing_state()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["factory_id"] == str(FACTORY_A)

    @pytest.mark.asyncio
    async def test_tier_reflected_in_response(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Response tier matches the factory's billing state."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(_make_pro_billing_state_with_grants()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["tier"] == "pro"

    @pytest.mark.asyncio
    async def test_response_has_audit_fields(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Response includes applied_grants, rejected_grants, audit_trail."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(_make_free_billing_state()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        assert isinstance(body["applied_grants"], list)
        assert isinstance(body["rejected_grants"], list)
        assert isinstance(body["audit_trail"], list)

    @pytest.mark.asyncio
    async def test_no_grants_empty_audit_trail(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Without grants, audit trail is empty and no grants applied/rejected."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(_make_free_billing_state()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        assert body["applied_grants"] == []
        assert body["rejected_grants"] == []
        assert body["audit_trail"] == []


# ──────────────────────────────────────────────────────────────────────
# 5. Cross-factory boundary
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsCrossFactoryBoundary:
    """Each factory only sees their own entitlements."""

    @pytest.mark.asyncio
    async def test_factory_a_sees_own_id(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """User from factory A gets entitlements for factory A."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(_make_free_billing_state()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.json()["factory_id"] == str(FACTORY_A)

    @pytest.mark.asyncio
    async def test_factory_b_sees_own_id(
        self, entitlements_app: FastAPI, user_b: User
    ) -> None:
        """User from factory B gets entitlements for factory B."""
        entitlements_app.dependency_overrides[get_current_user] = lambda: user_b

        with _patch_billing(_make_free_billing_state()):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        assert resp.json()["factory_id"] == str(FACTORY_B)

    @pytest.mark.asyncio
    async def test_grants_for_other_factory_are_filtered(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Grants belonging to factory B are invisible to factory A."""
        grants_for_b = [
            ManualGrant(
                factory_id=str(FACTORY_B),
                capability=Capability.PROJECT_COUNT,
                value=100,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@test.com",
            ),
        ]

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=grants_for_b)):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        # Factory A should NOT benefit from factory B's grant
        assert body["capabilities"]["project_count"] == 1  # FREE tier default
        assert body["applied_grants"] == []


# ──────────────────────────────────────────────────────────────────────
# 6. Engine evaluation through route — grants resolve correctly
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsEngineEvaluation:
    """Grants resolve correctly when routed through the endpoint."""

    @pytest.mark.asyncio
    async def test_active_grant_appears_in_applied(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """An active grant for factory A appears in applied_grants."""
        grant = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.AI_BUDGET,
            value=100,
            reason=GrantReason.SALES_DEAL,
            granted_by="sales@test.com",
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=[grant])):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        assert len(body["applied_grants"]) == 1
        assert body["applied_grants"][0]["capability"] == "ai_budget"
        assert body["applied_grants"][0]["value"] == 100
        assert body["applied_grants"][0]["reason"] == "sales_deal"

    @pytest.mark.asyncio
    async def test_expired_grant_appears_in_audit_trail(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Expired grant appears in audit_trail with disposition=expired."""
        expired_grant = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.AI_BUDGET,
            value=50,
            reason=GrantReason.TRIAL_EXTENSION,
            granted_by="admin@test.com",
            granted_at=datetime.now(UTC) - timedelta(days=10),
            expires_at=datetime.now(UTC) - timedelta(days=5),
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=[expired_grant])):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        assert len(body["audit_trail"]) == 1
        assert body["audit_trail"][0]["disposition"] == "expired"
        # Expired grant should NOT affect resolved value
        assert body["capabilities"]["ai_budget"] == 0  # FREE tier default

    @pytest.mark.asyncio
    async def test_numeric_grant_overrides_plan(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Grant with higher value overrides FREE tier project_count."""
        grant = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.PROJECT_COUNT,
            value=5,
            reason=GrantReason.ADMIN_OVERRIDE,
            granted_by="admin@test.com",
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=[grant])):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        # FREE tier default is 1, grant overrides to 5
        assert body["capabilities"]["project_count"] == 5

    @pytest.mark.asyncio
    async def test_boolean_grant_enables_disabled_capability(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Grant can enable production_export on FREE tier (False by default)."""
        grant = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.PRODUCTION_EXPORT,
            value=1,
            reason=GrantReason.SUPPORT_ESCALATION,
            granted_by="support@test.com",
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=[grant])):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        # FREE tier has production_export=False; grant overrides to True
        assert body["capabilities"]["production_export"] is True

    @pytest.mark.asyncio
    async def test_pro_tier_high_caps_not_degraded_by_free_grants(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """PRO tier caps stay at tier default when grants are lower."""
        small_grant = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.PROJECT_COUNT,
            value=2,
            reason=GrantReason.ADMIN_OVERRIDE,
            granted_by="admin@test.com",
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.PRO, grants=[small_grant])):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        # PRO tier has max_projects=10; grant=2 should NOT lower it
        assert body["capabilities"]["project_count"] == 10


# ──────────────────────────────────────────────────────────────────────
# 7. Audit trail integrity — all grant fields present
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsAuditTrailIntegrity:
    """Audit trail entries contain all required fields for downstream audit."""

    @pytest.mark.asyncio
    async def test_applied_grant_has_all_fields(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """Applied grant snapshot has factory_id, capability, value, reason, granted_by, timestamps."""
        grant = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.AI_BUDGET,
            value=200,
            reason=GrantReason.SALES_DEAL,
            granted_by="sales@test.com",
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=[grant])):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        entry = resp.json()["audit_trail"][0]
        required_keys = {
            "factory_id",
            "capability",
            "value",
            "reason",
            "granted_by",
            "granted_at",
            "expires_at",
            "disposition",
        }
        assert required_keys <= set(entry.keys())
        assert entry["disposition"] == "applied"

    @pytest.mark.asyncio
    async def test_superseded_grant_disposition(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """When two grants exist for the same cap, the lower one is superseded."""
        grant_high = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.PROJECT_COUNT,
            value=20,
            reason=GrantReason.ADMIN_OVERRIDE,
            granted_by="admin@test.com",
            granted_at=datetime.now(UTC),
        )
        grant_low = ManualGrant(
            factory_id=str(FACTORY_A),
            capability=Capability.PROJECT_COUNT,
            value=5,
            reason=GrantReason.TRIAL_EXTENSION,
            granted_by="admin@test.com",
            granted_at=datetime.now(UTC) - timedelta(hours=1),
        )

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(
            FactoryBillingState(tier=PlanTier.FREE, grants=[grant_high, grant_low])
        ):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        # Higher grant wins → capability = 20
        assert body["capabilities"]["project_count"] == 20

        # Both grants appear in audit trail
        dispositions = {e["disposition"] for e in body["audit_trail"]}
        assert "applied" in dispositions
        assert "superseded" in dispositions

    @pytest.mark.asyncio
    async def test_all_grant_reasons_serializable(
        self, entitlements_app: FastAPI, user_a: User
    ) -> None:
        """All GrantReason enum values serialize cleanly in audit trail."""
        grants = [
            ManualGrant(
                factory_id=str(FACTORY_A),
                capability=Capability.AI_BUDGET,
                value=10,
                reason=reason,
                granted_by="admin@test.com",
            )
            for reason in GrantReason
        ]

        entitlements_app.dependency_overrides[get_current_user] = lambda: user_a

        with _patch_billing(FactoryBillingState(tier=PlanTier.FREE, grants=grants)):
            transport = ASGITransport(app=entitlements_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/entitlements")

        body = resp.json()
        reasons_in_trail = {e["reason"] for e in body["audit_trail"]}
        for reason in GrantReason:
            assert reason.value in reasons_in_trail
