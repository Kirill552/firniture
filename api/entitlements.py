"""
Домен entitlements: типизированные capabilities, разрешение по плану + грантам.

Provider-agnostic: решает какие возможности доступны фабрике.
Интеграция с checkout/webhook — вне этого модуля (human control).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from .billing import GrantReason, ManualGrant, PlanLimits, PlanTier, get_plan_limits


class Capability(str, Enum):
    """Типизированные возможности фабрики.

    numeric=True — значение числовое (лимит).
    numeric=False — boolean (включено/выключено).
    """

    PROJECT_COUNT = "project_count"
    AI_BUDGET = "ai_budget"
    PREVIEW_EXPORT = "preview_export"
    PRODUCTION_EXPORT = "production_export"
    CERTIFIED_PROFILES = "certified_profiles"
    TEAM_SEATS = "team_seats"

    @property
    def numeric(self) -> bool:
        return self in (
            Capability.PROJECT_COUNT,
            Capability.AI_BUDGET,
            Capability.CERTIFIED_PROFILES,
            Capability.TEAM_SEATS,
        )


class GrantDisposition(str, Enum):
    """Disposition of a single grant in the audit trail.

    Every supplied grant appears exactly once in the complete audit trail.
    """

    EXPIRED = "expired"        # Grant is inactive (past expiry or wrong factory)
    APPLIED = "applied"        # Grant is active AND binding (determines the resolved value)
    SUPERSEDED = "superseded"  # Grant is active but NOT binding (a better grant wins)


@dataclass(frozen=True)
class GrantSnapshot:
    """Immutable snapshot of a ManualGrant captured at resolve time.

    Stores the grant's essential fields by value so that post-resolve
    mutations to the original ManualGrant cannot rewrite audit facts.
    """

    factory_id: str
    capability: Any
    value: int
    reason: GrantReason
    granted_by: str
    expires_at: datetime | None
    granted_at: datetime

    @classmethod
    def from_grant(cls, grant: ManualGrant) -> GrantSnapshot:
        """Snapshot a ManualGrant at the current moment."""
        return cls(
            factory_id=grant.factory_id,
            capability=grant.capability,
            value=grant.value,
            reason=grant.reason,
            granted_by=grant.granted_by,
            expires_at=grant.expires_at,
            granted_at=grant.granted_at,
        )


@dataclass(frozen=True)
class GrantAuditEntry:
    """A single entry in the complete audit trail for a grant."""

    grant: GrantSnapshot
    disposition: GrantDisposition

# ──────────────────────────────────────────────────────────────────────
# Маппинг capability → поле PlanLimits
# ──────────────────────────────────────────────────────────────────────

_CAPABILITY_TO_LIMIT_FIELD: dict[Capability, str] = {
    Capability.PROJECT_COUNT: "max_projects",
    Capability.AI_BUDGET: "ai_budget",
    Capability.PREVIEW_EXPORT: "preview_export",
    Capability.PRODUCTION_EXPORT: "production_export",
    Capability.CERTIFIED_PROFILES: "certified_profiles",
    Capability.TEAM_SEATS: "team_seats",
}


def _plan_value(limits: PlanLimits, cap: Capability) -> int | bool:
    """Извлечь значение capability из лимитов плана."""
    field_name = _CAPABILITY_TO_LIMIT_FIELD[cap]
    return getattr(limits, field_name)


# ──────────────────────────────────────────────────────────────────────
# Resolved capabilities
# ──────────────────────────────────────────────────────────────────────


@dataclass
class ResolvedCapabilities:
    """Итоговые capabilities для фабрики после разрешения плана + грантов."""

    project_count: int
    ai_budget: int
    preview_export: bool
    production_export: bool
    certified_profiles: int
    team_seats: int
    applied_grants: list[ManualGrant] = field(default_factory=list)
    rejected_grants: list[ManualGrant] = field(default_factory=list)
    audit_trail: list[GrantAuditEntry] = field(default_factory=list)

    def can_use(self, cap: Capability, *, current_usage: int) -> bool:
        """Проверить, может ли фабрика использовать ещё одну единицу capability."""
        value = _resolve_value(self, cap)
        if value == -1:  # unlimited
            return True
        if isinstance(value, bool):
            return value
        return current_usage < value


def _resolve_value(caps: ResolvedCapabilities, cap: Capability) -> int | bool:
    """Извлечь итоговое значение capability из ResolvedCapabilities."""
    return getattr(caps, cap.value)


# ──────────────────────────────────────────────────────────────────────
# Entitlements engine
# ──────────────────────────────────────────────────────────────────────


class EntitlementsEngine:
    """Разрешает capabilities для фабрики на основе плана и активных грантов.

    Не зависит от payment provider. Provider integration — human control.
    """

    def resolve(
        self,
        tier: PlanTier,
        *,
        factory_id: str,
        grants: list[ManualGrant] | None = None,
        now: datetime | None = None,
    ) -> ResolvedCapabilities:
        """
        Разрешить capabilities для фабрики.

        Алгоритм:
        1. Берём дефолтные лимиты из плана.
        2. Фильтруем гранты: только для этой фабрики + активные.
        3. Для числовых: max(план, максимальный_активный_грант).
           - unlimited (-1) всегда побеждает.
        4. Для boolean: True если план=True ИЛИ любой активный грант=1.
        5. Сохраняем applied/rejected для аудита.

        Args:
            tier: Тарифный план фабрики.
            factory_id: UUID фабрики (строка).
            grants: Список ручных грантов (могут быть от разных фабрик).
            now: Текущее время (для тестов). Если None — используется.utcnow().
        """
        check_time = now or datetime.now(UTC)
        limits = get_plan_limits(tier)
        grants = grants or []

        # Фильтруем гранты для этой фабрики
        relevant = [g for g in grants if g.factory_id == factory_id]

        # Разделяем активные / отклонённые
        active_grants: list[ManualGrant] = []
        rejected_grants: list[ManualGrant] = []
        for g in relevant:
            if g.is_active(now=check_time):
                active_grants.append(g)
            else:
                rejected_grants.append(g)

        # Разрешаем каждую capability
        resolved: dict[str, int | bool] = {}
        applied: list[ManualGrant] = []
        audit_trail: list[GrantAuditEntry] = []

        for cap in Capability:
            plan_val = _plan_value(limits, cap)
            relevant_active = [g for g in active_grants if g.capability == cap]

            if cap.numeric:
                value, binding_grant = _resolve_numeric(plan_val, relevant_active)
            else:
                value, binding_grant = _resolve_boolean(plan_val, relevant_active)

            resolved[cap.value] = value
            if binding_grant is not None:
                applied.append(binding_grant)

            # Audit trail: every active grant for this capability gets a disposition
            for g in relevant_active:
                if g is binding_grant:
                    disposition = GrantDisposition.APPLIED
                else:
                    disposition = GrantDisposition.SUPERSEDED
                audit_trail.append(GrantAuditEntry(grant=GrantSnapshot.from_grant(g), disposition=disposition))

        # Expired / wrong-factory grants: EXPIRED disposition
        for g in relevant:
            if not g.is_active(now=check_time):
                audit_trail.append(GrantAuditEntry(grant=GrantSnapshot.from_grant(g), disposition=GrantDisposition.EXPIRED))

        return ResolvedCapabilities(
            project_count=resolved[Capability.PROJECT_COUNT.value],
            ai_budget=resolved[Capability.AI_BUDGET.value],
            preview_export=resolved[Capability.PREVIEW_EXPORT.value],
            production_export=resolved[Capability.PRODUCTION_EXPORT.value],
            certified_profiles=resolved[Capability.CERTIFIED_PROFILES.value],
            team_seats=resolved[Capability.TEAM_SEATS.value],
            applied_grants=applied,
            rejected_grants=rejected_grants,
            audit_trail=audit_trail,
        )


def _resolve_numeric(
    plan_value: int, grants: list[ManualGrant]
) -> tuple[int, ManualGrant | None]:
    """Числовая capability: max(план, гранты). Unlimited (-1) побеждает всегда."""
    if plan_value == -1:
        return -1, None

    best_value = plan_value
    best_grant: ManualGrant | None = None

    for g in grants:
        if g.value == -1:
            return -1, g  # unlimited wins
        if g.value > best_value:
            best_value = g.value
            best_grant = g

    return best_value, best_grant


def _resolve_boolean(
    plan_value: bool, grants: list[ManualGrant]
) -> tuple[bool, ManualGrant | None]:
    """Boolean capability: True если план=True ИЛИ любой активный грант=1."""
    if plan_value:
        return True, None

    for g in grants:
        if g.value >= 1:
            return True, g

    return False, None
