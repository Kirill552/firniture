"""Entitlements route — provider-independent capability resolution.

GET /api/v1/entitlements
    Evaluates EntitlementsEngine for authenticated factory.
    Returns typed capabilities + audit-safe manual-grant state.

Паттерн:
    Routes — thin controller. Вся доменная логика в api.entitlements.
    Authorization — factory boundary implicit (own factory only).
    Persistence port — abstract dependency, returns 503 when not wired up.

Зависимости:
    api.entitlements       — EntitlementsEngine, ResolvedCapabilities, Capability
    api.billing            — PlanTier, ManualGrant, GrantReason
    api.auth               — get_current_user
    api.models             — User

Ограничения:
    Не модифицирует api.entitlements, api.billing, api.routers, models, frontend.
    Провайдер/checkout/webhook — вне этого модуля.
    Регистрация — явная через app.include_router(entitlements_router).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import get_current_user
from api.billing import ManualGrant, PlanTier
from api.entitlements import (
    Capability,
    EntitlementsEngine,
    GrantAuditEntry,
    ResolvedCapabilities,
)
from api.models import User

# ──────────────────────────────────────────────────────────────────────
# Persistence port: abstract interface for loading billing state
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FactoryBillingState:
    """Immutable billing state for a factory.

    Loaded from persistence layer. When persistence is absent,
    the default dependency returns None and the route returns 503.
    """

    tier: PlanTier
    grants: list[ManualGrant]


# ──────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────


class EntitlementsResponse(BaseModel):
    """Response from GET /api/v1/entitlements.

    Capabilities as a flat dict keyed by Capability enum value.
    Grant snapshots are audit-safe: serialised from frozen GrantSnapshot
    objects captured at resolve time.
    """

    factory_id: str
    tier: str
    capabilities: dict[str, Any]
    applied_grants: list[dict[str, Any]]
    rejected_grants: list[dict[str, Any]]
    audit_trail: list[dict[str, Any]]


# ──────────────────────────────────────────────────────────────────────
# Persistence dependency (abstract — not wired up)
# ──────────────────────────────────────────────────────────────────────


async def _load_factory_billing_state(
    factory_id: str,
) -> FactoryBillingState | None:
    """Load billing state for a factory by ID.

    Default implementation returns None: persistence layer is absent.
    Replace via dependency_overrides or a concrete loader when the
    billing provider is integrated.

    This is the explicit persistence port. No checkout, webhook,
    or provider credential logic belongs here.
    """
    return None


# ──────────────────────────────────────────────────────────────────────
# Serialisation helpers
# ──────────────────────────────────────────────────────────────────────


def _capability_str(cap: Capability | object) -> str:
    """Extract string value from a Capability enum or raw object."""
    if hasattr(cap, "value"):
        return cap.value  # type: ignore[union-attr]
    return str(cap)


def _grant_to_dict(grant: ManualGrant) -> dict[str, Any]:
    """Serialize ManualGrant for audit-safe JSON output."""
    return {
        "factory_id": grant.factory_id,
        "capability": _capability_str(grant.capability),
        "value": grant.value,
        "reason": grant.reason.value,
        "granted_by": grant.granted_by,
        "granted_at": grant.granted_at.isoformat(),
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
    }


def _audit_entry_to_dict(entry: GrantAuditEntry) -> dict[str, Any]:
    """Serialize GrantAuditEntry for audit-safe JSON output."""
    snap = entry.grant
    return {
        "factory_id": snap.factory_id,
        "capability": _capability_str(snap.capability),
        "value": snap.value,
        "reason": snap.reason.value,
        "granted_by": snap.granted_by,
        "granted_at": snap.granted_at.isoformat(),
        "expires_at": snap.expires_at.isoformat() if snap.expires_at else None,
        "disposition": entry.disposition.value,
    }


# ──────────────────────────────────────────────────────────────────────
# Engine singleton (stateless, safe to share)
# ──────────────────────────────────────────────────────────────────────

_engine = EntitlementsEngine()


# ──────────────────────────────────────────────────────────────────────
# Route
# ──────────────────────────────────────────────────────────────────────

entitlements_router = APIRouter(prefix="/api/v1/entitlements", tags=["Entitlements"])


@entitlements_router.get(
    "",
    response_model=EntitlementsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_entitlements(
    user: User = Depends(get_current_user),
) -> EntitlementsResponse:
    """Resolve and return capabilities for the authenticated factory.

    Requires:
    - Authenticated user (get_current_user)
    - Factory billing state (load_factory_billing_state)

    Returns typed capabilities (project_count, ai_budget, etc.) plus
    audit-safe grant state (applied, rejected, full audit trail with
    dispositions for every supplied grant).

    Cross-factory boundary:
    - Resolves ONLY for user.factory_id. There is no way to request
      another factory's entitlements through this endpoint.

    Does NOT:
    - Access any payment provider
    - Create/modify/delete grants
    - Make checkout or webhook calls
    - Persist data

    When persistence is not wired up (default), returns 503 with a
    clear message indicating what needs to be implemented.
    """
    # Load billing state for this factory
    billing_state = await _load_factory_billing_state(str(user.factory_id))

    # 503: persistence layer not integrated
    if billing_state is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Billing persistence not integrated. "
                "Wire _load_factory_billing_state to return "
                "FactoryBillingState(tier, grants) for the requesting factory. "
                "This is a provider decision — no checkout/webhook code here."
            ),
        )

    # Evaluate engine for authenticated factory only
    resolved: ResolvedCapabilities = _engine.resolve(
        billing_state.tier,
        factory_id=str(user.factory_id),
        grants=billing_state.grants,
    )

    capabilities: dict[str, Any] = {
        cap.value: getattr(resolved, cap.value)
        for cap in Capability
    }

    return EntitlementsResponse(
        factory_id=str(user.factory_id),
        tier=billing_state.tier.value,
        capabilities=capabilities,
        applied_grants=[_grant_to_dict(g) for g in resolved.applied_grants],
        rejected_grants=[_grant_to_dict(g) for g in resolved.rejected_grants],
        audit_trail=[_audit_entry_to_dict(e) for e in resolved.audit_trail],
    )
