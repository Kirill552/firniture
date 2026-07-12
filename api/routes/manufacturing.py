"""Manufacturing approval routes — Task 8 (только).

Точное соответствие плану:
- POST /api/v1/orders/{order_id}/manufacturing/validate
- POST /api/v1/orders/{order_id}/manufacturing/approve
- Авторизация + tenant isolation
- Stale revision rejection (409)
- Подтверждение технологом (confirmed)
- Audit log без AI prompts
- Gate для PDF/DXF (используется в других роутах через assert_approved_for_export)

G-code routes — disabled, вне пилота.
Минимальные регистрации — только подключение этого модуля.

Routes — тонкие. Вся логика в api/manufacturing/approvals.py + crud.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_current_user
from api.crud import (
    get_latest_revision_for_order,
    get_order_with_products,
)
from api.database import get_db
from api.manufacturing.approvals import (
    ApprovalDecision,
    ApprovalError,
    ApprovalRequest,
    ApprovalResponse,
    ConfirmationRequiredError,
    CrossFactoryDenialError,
    NotApprovedForExportError,
    RevisionMismatchError,
    TechnologistRequiredError,
    ValidateResponse,
    assert_approved_for_export,
    build_audit_payload,
    compute_new_status,
    enforce_tenant_isolation,
    reject_stale_revision,
    require_authenticated_technologist,
    require_technologist_confirmation,
    validate_for_technologist,
    validate_reviewable,
)
from api.models import AuditLog, ManufacturingRevision, Order, RevisionStatusEnum, User

router = APIRouter(prefix="/api/v1", tags=["Manufacturing Approvals (Task 8)"])

# Ветка уже содержит клиентов/тесты раннего revision-level API. Оставляем
# совместимые маршруты до миграции клиентов на order-level API ниже.
_legacy_router = APIRouter(prefix="/api/v1/manufacturing", tags=["Manufacturing Approvals (legacy)"])


class _LegacyApprovalRequest(BaseModel):
    """Тело совместимого revision-level approve/reject запроса."""

    decision: ApprovalDecision = Field(...)
    expected_revision: int = Field(..., ge=1)
    comment: str | None = Field(None, max_length=2000)


async def _get_revision_or_404(db: AsyncSession, revision_id: UUID) -> ManufacturingRevision:
    result = await db.execute(
        select(ManufacturingRevision)
        .options(selectinload(ManufacturingRevision.order))
        .where(ManufacturingRevision.id == revision_id)
    )
    revision = result.scalar_one_or_none()
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    return revision


def _legacy_error_to_http(exc: ApprovalError) -> HTTPException:
    if isinstance(exc, RevisionMismatchError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "revision_mismatch",
                "message": str(exc),
                "expected": exc.expected,
                "actual": exc.actual,
            },
        )
    return _error_to_http(exc)


async def _legacy_decide_revision(
    revision_id: UUID,
    req: _LegacyApprovalRequest,
    db: AsyncSession,
    user: User | None,
    *,
    forced_decision: ApprovalDecision | None = None,
) -> dict:
    """Выполнить старое решение по revision-level API без AI-данных в audit."""
    try:
        user = require_authenticated_technologist(user)
        revision = await _get_revision_or_404(db, revision_id)
        if revision.order is None:
            raise CrossFactoryDenialError()
        enforce_tenant_isolation(revision.order, user)
        reject_stale_revision(revision, req.expected_revision)
        validate_reviewable(revision)

        decision = forced_decision or req.decision
        revision.status = compute_new_status(decision)
        revision.needs_review = False
        if revision.order is not None:
            revision.order.manufacturing_status = (
                "approved" if decision == ApprovalDecision.APPROVED else "rejected"
            )
            if decision == ApprovalDecision.APPROVED:
                revision.order.approved_manufacturing_revision = revision.revision_number
            revision.order.manufacturing_revision = revision.revision_number

        now = datetime.now(UTC).isoformat()
        audit = {
            "revision_id": str(revision.id),
            "user_id": str(user.id),
            "factory_id": str(user.factory_id),
            "decision": decision.value,
            "expected_revision": req.expected_revision,
            "actual_revision": revision.revision_number,
            "comment": req.comment,
            "timestamp": now,
            "metadata": {"source": "technologist_manual_approval"},
        }
        db.add(
            AuditLog(
                actor_role="technologist",
                action=("revision_approved" if decision == ApprovalDecision.APPROVED else "revision_rejected"),
                entity="manufacturing_revision",
                entity_id=revision.id,
                details=audit,
            )
        )
        db.add(revision)
        db.add(revision.order)
        await db.commit()
        await db.refresh(revision)
        return {
            "revision_id": revision.id,
            "decision": decision.value,
            "new_status": revision.status,
            "revision_number": revision.revision_number,
            "audit": audit,
        }
    except ApprovalError as exc:
        await db.rollback()
        raise _legacy_error_to_http(exc) from exc
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise


# ============================================================================
# Helpers (минимальные, для тонких routes)
# ============================================================================


async def _get_order_or_404(db: AsyncSession, order_id: UUID) -> Order:
    order = await get_order_with_products(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order {order_id} не найден")
    return order


async def _get_latest_revision_or_404(db: AsyncSession, order_id: UUID) -> ManufacturingRevision:
    rev = await get_latest_revision_for_order(db, order_id)
    if rev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Для заказа нет manufacturing revision. Сначала сгенерируйте спецификацию.",
        )
    return rev


def _error_to_http(exc: ApprovalError) -> HTTPException:
    if isinstance(exc, TechnologistRequiredError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if isinstance(exc, CrossFactoryDenialError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, RevisionMismatchError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "stale_revision", "message": str(exc), "expected": exc.expected, "actual": exc.actual},
        )
    if isinstance(exc, NotApprovedForExportError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "not_approved", "message": str(exc)})
    if isinstance(exc, ConfirmationRequiredError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    # generic
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ============================================================================
# Endpoints per Task 8
# ============================================================================


@router.post(
    "/orders/{order_id}/manufacturing/validate",
    response_model=ValidateResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_manufacturing(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> ValidateResponse:
    """Валидация текущей ревизии перед утверждением.

    Возвращает blocking_errors, warnings и точные ссылки на операции.
    Требует аутентификации + tenant.
    """
    try:
        user = require_authenticated_technologist(user)
        order = await _get_order_or_404(db, order_id)
        enforce_tenant_isolation(order, user)

        rev = await _get_latest_revision_or_404(db, order_id)
        # spec хранится в rev.spec как canonical dict
        spec_dict = rev.spec or {}
        return validate_for_technologist(order_id, rev.revision_number, spec_dict)
    except ApprovalError as exc:
        raise _error_to_http(exc) from exc


@router.post(
    "/orders/{order_id}/manufacturing/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_manufacturing(
    order_id: UUID,
    req: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> ApprovalResponse:
    """Настоящее утверждение технологом.

    - expected_revision (stale → 409)
    - confirmed=true обязательно (технолог подтверждает)
    - tenant isolation + auth
    - обновляет revision.status + order.approved_manufacturing_revision
    - пишет AuditLog без каких-либо AI prompt'ов
    """
    try:
        # 1. Auth + confirmation
        user = require_authenticated_technologist(user)
        require_technologist_confirmation(req.confirmed)

        # 2. Load
        order = await _get_order_or_404(db, order_id)
        enforce_tenant_isolation(order, user)

        rev = await _get_latest_revision_or_404(db, order_id)

        # 3. Stale rejection (TDD)
        reject_stale_revision(rev, req.expected_revision)

        # 4. Status
        validate_reviewable(rev)

        # 5. Apply
        decision = ApprovalDecision.APPROVED  # в пилоте approve только; reject отдельно если нужно
        new_status = compute_new_status(decision)
        rev.status = new_status
        rev.needs_review = False

        # Обновляем order state (SSOT для gate'ов)
        order.approved_manufacturing_revision = rev.revision_number
        order.manufacturing_revision = rev.revision_number
        order.manufacturing_status = "approved"
        order.updated_at = order.updated_at  # touch

        # 6. Audit (строго без AI)
        h = rev.provenance.get("spec_hash") if rev.provenance else None
        audit = build_audit_payload(
            revision_id=rev.id,
            user=user,
            decision=decision,
            expected_revision=req.expected_revision,
            actual_revision=rev.revision_number,
            confirmed=req.confirmed,
            comment=req.comment,
            spec_hash_value=h,
        )

        audit_log = AuditLog(
            actor_role="technologist",
            action="manufacturing_approve",
            entity="manufacturing_revision",
            entity_id=rev.id,
            details=audit,
        )
        db.add(audit_log)
        db.add(rev)
        db.add(order)
        await db.commit()
        await db.refresh(rev)
        await db.refresh(order)

        return ApprovalResponse(
            revision_id=rev.id,
            decision=decision,
            new_status=new_status,
            revision_number=rev.revision_number,
            order_manufacturing_status=order.manufacturing_status,
            audit=audit,
        )

    except ApprovalError as exc:
        await db.rollback()
        raise _error_to_http(exc) from exc
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise


@_legacy_router.post("/revisions/{revision_id}/approve")
async def legacy_approve_revision(
    revision_id: UUID,
    req: _LegacyApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    """Совместимый revision-level approve маршрут для старых клиентов."""
    return await _legacy_decide_revision(revision_id, req, db, user)


@_legacy_router.post("/revisions/{revision_id}/reject")
async def legacy_reject_revision(
    revision_id: UUID,
    req: _LegacyApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    """Совместимый revision-level reject маршрут для старых клиентов."""
    return await _legacy_decide_revision(
        revision_id,
        req,
        db,
        user,
        forced_decision=ApprovalDecision.REJECTED,
    )


@_legacy_router.get("/revisions/{revision_id}/cam-gate")
async def legacy_cam_gate(
    revision_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    """Совместимый read-only gate: CAM допускается только approved revision."""
    try:
        user = require_authenticated_technologist(user)
        revision = await _get_revision_or_404(db, revision_id)
        if revision.order is None:
            raise CrossFactoryDenialError()
        enforce_tenant_isolation(revision.order, user)
    except ApprovalError as exc:
        raise _legacy_error_to_http(exc) from exc

    passed = revision.status == RevisionStatusEnum.APPROVED
    return {
        "revision_id": revision.id,
        "revision_status": revision.status,
        "gate_passed": passed,
        "reason": None if passed else "Revision is not approved",
    }


# ============================================================================
# Gate helper для использования в DXF/PDF routes (Task 8 Step 5)
# ============================================================================


async def assert_order_export_gate(db: AsyncSession, order_id: UUID) -> None:
    """Вызывается из DXF/PDF генераторов. 409 если нет approved revision."""
    order = await get_order_with_products(db, order_id)
    if order is None:
        raise HTTPException(404, "Order not found for gate")
    rev = await get_latest_revision_for_order(db, order_id)
    try:
        assert_approved_for_export(rev, order)
    except NotApprovedForExportError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "export_gate_failed", "message": str(exc.detail)},
        ) from exc


# Маршруты уже содержат полный префикс в ``route.path``. Это сохраняет
# совместимость с контрактом раннего API, который проверяет ``router.prefix``.
router.routes.extend(_legacy_router.routes)
router.prefix = "/api/v1/manufacturing"
