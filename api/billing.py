"""
Определения тарифных планов и ручных грантов.

Provider-agnostic: никакого интегрированного checkout / webhook / Stripe.
Интеграция с payment provider — human control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class PlanTier(str, Enum):
    """Тарифные планы."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class GrantReason(str, Enum):
    """Причина ручного гранта (аудит)."""

    ADMIN_OVERRIDE = "admin_override"
    TRIAL_EXTENSION = "trial_extension"
    SALES_DEAL = "sales_deal"
    SUPPORT_ESCALATION = "support_escalation"


# ──────────────────────────────────────────────────────────────────────
# Лимиты планов
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanLimits:
    """Лимиты тарифного плана.

    Числовые значения: -1 = без ограничений (unlimited).
    Булевы: True/False.
    """

    max_projects: int  # -1 = unlimited
    ai_budget: int  # -1 = unlimited; количество AI-операций в месяц
    preview_export: bool
    production_export: bool
    certified_profiles: int  # -1 = unlimited; количество доступных профилей станков
    team_seats: int  # -1 = unlimited


# ──────────────────────────────────────────────────────────────────────
# Дефолтные лимиты по планам
# ──────────────────────────────────────────────────────────────────────

_PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.FREE: PlanLimits(
        max_projects=1,
        ai_budget=0,
        preview_export=True,
        production_export=False,
        certified_profiles=1,
        team_seats=1,
    ),
    PlanTier.STARTER: PlanLimits(
        max_projects=3,
        ai_budget=50,
        preview_export=True,
        production_export=True,
        certified_profiles=3,
        team_seats=3,
    ),
    PlanTier.PRO: PlanLimits(
        max_projects=10,
        ai_budget=200,
        preview_export=True,
        production_export=True,
        certified_profiles=-1,  # все профили
        team_seats=10,
    ),
    PlanTier.ENTERPRISE: PlanLimits(
        max_projects=-1,
        ai_budget=-1,
        preview_export=True,
        production_export=True,
        certified_profiles=-1,
        team_seats=-1,
    ),
}


def get_plan_limits(tier: PlanTier) -> PlanLimits:
    """Вернуть лимиты для тарифного плана."""
    return _PLAN_LIMITS[tier]


# ──────────────────────────────────────────────────────────────────────
# Ручные гранты
# ──────────────────────────────────────────────────────────────────────


@dataclass
class ManualGrant:
    """Ручной грант — временный override capability для фабрики.

    Гранты накапливаются; для числовых capabilities берётся максимум.
    Для boolean — если хотя бы один грант активен, capability = True.
    """

    factory_id: str
    capability: Any  # Capability из entitlements (избегаем циклического импорта)
    value: int  # числовое значение или 1/0 для boolean
    reason: GrantReason
    granted_by: str
    expires_at: datetime | None = None
    granted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_active(self, *, now: datetime | None = None) -> bool:
        """Проверить, активен ли грант на данный момент."""
        if self.expires_at is None:
            return True
        check_time = now or datetime.now(UTC)
        return self.expires_at > check_time
