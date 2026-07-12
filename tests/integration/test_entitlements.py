"""
Интеграционные тесты домена entitlements.

Проверяет:
- Определение типизированных возможностей (capabilities) по тарифному плану
- Решение о доступности возможностей для фабрики
- Ручные гранты с ограничением по времени и аудитом
- Интеграцию: план + гранты → итоговые capabilities

Нет provider-specific кода (Stripe, webhook и т.д.).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.billing import (
    GrantReason,
    ManualGrant,
    PlanTier,
    get_plan_limits,
)
from api.entitlements import (
    Capability,
    EntitlementsEngine,
    GrantSnapshot,
    ResolvedCapabilities,
)

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────

FACTORY_ID_1 = "11111111-1111-1111-1111-111111111111"
FACTORY_ID_2 = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def engine() -> EntitlementsEngine:
    return EntitlementsEngine()


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


# ──────────────────────────────────────────────────────────────────────
# 1. Планы и лимиты
# ──────────────────────────────────────────────────────────────────────


class TestPlanLimits:
    """Каждый тариф определяет набор лимитов."""

    def test_free_plan_exists(self):
        limits = get_plan_limits(PlanTier.FREE)
        assert limits is not None
        assert limits.max_projects == 1
        assert limits.ai_budget == 0

    def test_starter_plan_exists(self):
        limits = get_plan_limits(PlanTier.STARTER)
        assert limits.max_projects == 3
        assert limits.ai_budget == 50

    def test_pro_plan_exists(self):
        limits = get_plan_limits(PlanTier.PRO)
        assert limits.max_projects == 10
        assert limits.ai_budget == 200

    def test_enterprise_plan_exists(self):
        limits = get_plan_limits(PlanTier.ENTERPRISE)
        assert limits.max_projects == -1  # unlimited
        assert limits.ai_budget == -1  # unlimited

    def test_all_plans_define_all_capabilities(self):
        """Каждый план содержит лимиты для всех 6 capabilities."""
        for tier in PlanTier:
            limits = get_plan_limits(tier)
            # Проверяем что все 6 ключевых полей присутствуют
            assert limits.max_projects is not None
            assert limits.ai_budget is not None
            assert limits.preview_export is not None
            assert limits.production_export is not None
            assert limits.certified_profiles is not None
            assert limits.team_seats is not None

    def test_tier_ordering_free_leasts(self):
        """FREE — минимум, ENTERPRISE — максимум (с учётом -1 = unlimited)."""
        free = get_plan_limits(PlanTier.FREE)
        ent = get_plan_limits(PlanTier.ENTERPRISE)
        # unlimited (-1) побеждает; сравниваем через resolve
        def effective(v: int) -> int:
            return v if v != -1 else float("inf")  # type: ignore[return-value]
        assert effective(free.max_projects) <= effective(ent.max_projects)
        assert effective(free.team_seats) <= effective(ent.team_seats)


# ──────────────────────────────────────────────────────────────────────
# 2. Capability enum
# ──────────────────────────────────────────────────────────────────────


class TestCapability:
    """Все 6 типизированных capabilities определены."""

    def test_all_six_capabilities_exist(self):
        expected = {
            "PROJECT_COUNT",
            "AI_BUDGET",
            "PREVIEW_EXPORT",
            "PRODUCTION_EXPORT",
            "CERTIFIED_PROFILES",
            "TEAM_SEATS",
        }
        actual = {cap.name for cap in Capability}
        assert actual == expected

    def test_capability_has_numeric_value(self):
        """PROJECT_COUNT и AI_BUDGET — числовые."""
        assert Capability.PROJECT_COUNT.numeric is True
        assert Capability.AI_BUDGET.numeric is True
        assert Capability.PREVIEW_EXPORT.numeric is False


# ──────────────────────────────────────────────────────────────────────
# 3. Engine: resolve capabilities по плану
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsEngineResolve:
    """Engine разрешает capabilities для фабрики по плану."""

    def test_free_plan_capabilities(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.FREE, factory_id=FACTORY_ID_1)
        assert caps.project_count == 1
        assert caps.ai_budget == 0
        assert caps.preview_export is True
        assert caps.production_export is False
        assert caps.team_seats == 1
        assert isinstance(caps, ResolvedCapabilities)

    def test_starter_plan_capabilities(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.STARTER, factory_id=FACTORY_ID_1)
        assert caps.project_count == 3
        assert caps.ai_budget == 50
        assert caps.production_export is True
        assert caps.team_seats == 3

    def test_pro_plan_capabilities(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.PRO, factory_id=FACTORY_ID_1)
        assert caps.project_count == 10
        assert caps.ai_budget == 200
        assert caps.team_seats == 10

    def test_enterprise_unlimited(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.ENTERPRISE, factory_id=FACTORY_ID_1)
        assert caps.project_count == -1
        assert caps.ai_budget == -1
        assert caps.team_seats == -1  # unlimited


# ──────────────────────────────────────────────────────────────────────
# 4. Manual grants
# ──────────────────────────────────────────────────────────────────────


class TestManualGrants:
    """Ручные гранты с ограничением по времени и аудитом."""

    def test_grant_creation(self, now: datetime):
        grant = ManualGrant(
            factory_id=FACTORY_ID_1,
            capability=Capability.PROJECT_COUNT,
            value=5,
            reason=GrantReason.ADMIN_OVERRIDE,
            granted_by="admin@mebel.ai",
            expires_at=now + timedelta(days=30),
        )
        assert grant.factory_id == FACTORY_ID_1
        assert grant.capability == Capability.PROJECT_COUNT
        assert grant.value == 5
        assert grant.is_active(now=now) is True

    def test_grant_expiry(self, now: datetime):
        grant = ManualGrant(
            factory_id=FACTORY_ID_1,
            capability=Capability.AI_BUDGET,
            value=100,
            reason=GrantReason.TRIAL_EXTENSION,
            granted_by="admin@mebel.ai",
            expires_at=now - timedelta(days=1),  # уже истёк
        )
        assert grant.is_active(now=now) is False

    def test_grant_without_expiry_is_permanent(self, now: datetime):
        grant = ManualGrant(
            factory_id=FACTORY_ID_1,
            capability=Capability.TEAM_SEATS,
            value=20,
            reason=GrantReason.SALES_DEAL,
            granted_by="sales@mebel.ai",
            expires_at=None,
        )
        assert grant.is_active(now=now) is True

    def test_grant_audit_fields(self, now: datetime):
        grant = ManualGrant(
            factory_id=FACTORY_ID_1,
            capability=Capability.CERTIFIED_PROFILES,
            value=3,
            reason=GrantReason.SUPPORT_ESCALATION,
            granted_by="support@mebel.ai",
            expires_at=now + timedelta(days=7),
        )
        assert grant.granted_by == "support@mebel.ai"
        assert grant.granted_at is not None
        assert grant.reason == GrantReason.SUPPORT_ESCALATION


# ──────────────────────────────────────────────────────────────────────
# 5. Engine: resolve с учётом грантов
# ──────────────────────────────────────────────────────────────────────


class TestEntitlementsWithGrants:
    """Гранты叠加ываются поверх плана."""

    def test_grant_overrides_plan_numeric(self, engine: EntitlementsEngine, now: datetime):
        """Грант на PROJECT_COUNT поверх FREE плана."""
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=5,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=30),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        # Грант заменяет плановый лимит (берём максимум)
        assert caps.project_count == 5

    def test_grant_does_not_apply_to_other_factory(
        self, engine: EntitlementsEngine, now: datetime
    ):
        """Грант для фабрики 1 не влияет на фабрику 2."""
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.TEAM_SEATS,
                value=50,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=30),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_2,
            grants=grants,
            now=now,
        )
        assert caps.team_seats == 1  # FREE default

    def test_expired_grant_ignored(self, engine: EntitlementsEngine, now: datetime):
        """Истёкший грант не влияет на capabilities."""
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.AI_BUDGET,
                value=999,
                reason=GrantReason.TRIAL_EXTENSION,
                granted_by="admin@mebel.ai",
                expires_at=now - timedelta(days=1),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        assert caps.ai_budget == 0  # FREE default, expired grant ignored

    def test_boolean_grant_enables_feature(self, engine: EntitlementsEngine, now: datetime):
        """Грант на boolean capability включает его."""
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PRODUCTION_EXPORT,
                value=1,  # 1 = True
                reason=GrantReason.SALES_DEAL,
                granted_by="sales@mebel.ai",
                expires_at=now + timedelta(days=14),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        assert caps.production_export is True

    def test_multiple_grants_cumulative(self, engine: EntitlementsEngine, now: datetime):
        """Несколько грантов叠加ываются (максимальный для числовых)."""
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=3,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=30),
            ),
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=8,
                reason=GrantReason.SALES_DEAL,
                granted_by="sales@mebel.ai",
                expires_at=now + timedelta(days=60),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        # Берём максимум из грантов для числовых
        assert caps.project_count == 8

    def test_enterprise_plan_not_decreased_by_grant(
        self, engine: EntitlementsEngine, now: datetime
    ):
        """Грант не может уменьшить план (enterprise unlimited не становится 5)."""
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=5,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=30),
            ),
        ]
        caps = engine.resolve(
            PlanTier.ENTERPRISE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        assert caps.project_count == -1  # unlimited wins over grant


# ──────────────────────────────────────────────────────────────────────
# 6. Audit trail
# ──────────────────────────────────────────────────────────────────────


class TestAuditTrail:
    """Engine фиксирует какие гранты были применены."""

    def test_resolve_returns_applied_grants(self, engine: EntitlementsEngine, now: datetime):
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=5,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=30),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        assert len(caps.applied_grants) == 1
        assert caps.applied_grants[0].capability == Capability.PROJECT_COUNT

    def test_resolve_records_rejected_expired(self, engine: EntitlementsEngine, now: datetime):
        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.AI_BUDGET,
                value=999,
                reason=GrantReason.TRIAL_EXTENSION,
                granted_by="admin@mebel.ai",
                expires_at=now - timedelta(days=1),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        assert len(caps.applied_grants) == 0
        assert len(caps.rejected_grants) == 1
        assert caps.rejected_grants[0].capability == Capability.AI_BUDGET
# ──────────────────────────────────────────────────────────────────────
# 6b. Audit trail: complete disposition coverage
# ──────────────────────────────────────────────────────────────────────


class TestAuditTrailCompleteDisposition:
    """Каждый поставляемый грант должен появляться ровно один раз в audit_trail."""

    def test_two_active_grants_larger_wins_lower_auditable(
        self, engine: EntitlementsEngine, now: datetime
    ):
        """Два активных гранта на одну capability: больший побеждает,
        меньший остаётся видимым в audit_trail как superseded."""
        from api.entitlements import GrantDisposition

        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=3,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=30),
            ),
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=8,
                reason=GrantReason.SALES_DEAL,
                granted_by="sales@mebel.ai",
                expires_at=now + timedelta(days=60),
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        # Resolver semantics: max wins
        assert caps.project_count == 8

        # Каждый грант — ровно один раз в audit_trail
        assert len(caps.audit_trail) == len(grants)

        by_value = {entry.grant.value: entry.disposition for entry in caps.audit_trail}
        assert by_value[8] == GrantDisposition.APPLIED
        assert by_value[3] == GrantDisposition.SUPERSEDED

    def test_mixed_dispositions_all_grants_accounted(
        self, engine: EntitlementsEngine, now: datetime
    ):
        """Истёкший + два активных (один binding, один superseded) —
        все три в audit_trail, ни один не потерян."""
        from api.entitlements import GrantDisposition

        grants = [
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=2,
                reason=GrantReason.ADMIN_OVERRIDE,
                granted_by="admin@mebel.ai",
                expires_at=now - timedelta(days=5),  # expired
            ),
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=4,
                reason=GrantReason.TRIAL_EXTENSION,
                granted_by="admin@mebel.ai",
                expires_at=now + timedelta(days=10),  # active, superseded
            ),
            ManualGrant(
                factory_id=FACTORY_ID_1,
                capability=Capability.PROJECT_COUNT,
                value=9,
                reason=GrantReason.SALES_DEAL,
                granted_by="sales@mebel.ai",
                expires_at=now + timedelta(days=30),  # active, binding
            ),
        ]
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=grants,
            now=now,
        )
        assert caps.project_count == 9
        assert len(caps.audit_trail) == len(grants)

        by_value = {entry.grant.value: entry.disposition for entry in caps.audit_trail}
        assert by_value[9] == GrantDisposition.APPLIED
        assert by_value[4] == GrantDisposition.SUPERSEDED
        assert by_value[2] == GrantDisposition.EXPIRED

        # Backward compat: applied/rejected still work
        assert len(caps.applied_grants) == 1
        assert caps.applied_grants[0].value == 9
        assert len(caps.rejected_grants) == 1
        assert caps.rejected_grants[0].value == 2


# ──────────────────────────────────────────────────────────────────────
# 6c. Audit trail: snapshot immutability
# ──────────────────────────────────────────────────────────────────────


class TestAuditSnapshotImmutability:
    """Audit trail stores snapshots; post-resolve mutations cannot rewrite facts."""

    def test_muting_source_grant_does_not_rewrite_audit(
        self, engine: EntitlementsEngine, now: datetime
    ):
        """Mutating the original ManualGrant after resolve must not change
        the audit trail — the trail holds GrantSnapshot copies."""
        grant = ManualGrant(
            factory_id=FACTORY_ID_1,
            capability=Capability.PROJECT_COUNT,
            value=5,
            reason=GrantReason.ADMIN_OVERRIDE,
            granted_by="admin@mebel.ai",
            expires_at=now + timedelta(days=30),
        )
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=[grant],
            now=now,
        )

        # Snapshot recorded original value
        assert len(caps.audit_trail) == 1
        original_entry = caps.audit_trail[0]
        assert original_entry.grant.value == 5
        assert original_entry.grant.capability == Capability.PROJECT_COUNT
        assert isinstance(original_entry.grant, GrantSnapshot)

        # Mutate the source grant after resolve
        grant.value = 999
        grant.capability = Capability.AI_BUDGET

        # Audit trail must still reflect original values
        assert original_entry.grant.value == 5
        assert original_entry.grant.capability == Capability.PROJECT_COUNT

    def test_snapshot_is_frozen(self, engine: EntitlementsEngine, now: datetime):
        """GrantSnapshot itself is immutable — reassignment raises FrozenInstanceError."""
        grant = ManualGrant(
            factory_id=FACTORY_ID_1,
            capability=Capability.PROJECT_COUNT,
            value=5,
            reason=GrantReason.ADMIN_OVERRIDE,
            granted_by="admin@mebel.ai",
            expires_at=now + timedelta(days=30),
        )
        caps = engine.resolve(
            PlanTier.FREE,
            factory_id=FACTORY_ID_1,
            grants=[grant],
            now=now,
        )
        snapshot = caps.audit_trail[0].grant
        with pytest.raises(AttributeError):
            snapshot.value = 999  # type: ignore[misc]
# ──────────────────────────────────────────────────────────────────────
# 7. Usage check helpers
# ──────────────────────────────────────────────────────────────────────


class TestUsageCheck:
    """Проверка использования квоты."""

    def test_can_create_project_within_limit(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.STARTER, factory_id=FACTORY_ID_1)
        assert caps.can_use(Capability.PROJECT_COUNT, current_usage=2) is True

    def test_cannot_create_project_at_limit(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.STARTER, factory_id=FACTORY_ID_1)
        assert caps.can_use(Capability.PROJECT_COUNT, current_usage=3) is False

    def test_unlimited_always_allows(self, engine: EntitlementsEngine):
        caps = engine.resolve(PlanTier.ENTERPRISE, factory_id=FACTORY_ID_1)
        assert caps.can_use(Capability.PROJECT_COUNT, current_usage=9999) is True
