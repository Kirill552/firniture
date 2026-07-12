"""Manufacturing approval domain — Task 8: настоящее утверждение технологом для пилота.

Только ручное утверждение ревизии технологом.
- authorization + tenant isolation
- stale revision rejection (expected_revision)
- validate endpoint (blocking errors + warnings + op refs)
- approve endpoint с expected_revision + подтверждением технолога (confirmed)
- audit log БЕЗ AI prompts (who/when/revision/hash/summary)
- gate PDF/DXF → 409 если нет approved revision
G-code полностью вне scope и disabled.

Паттерн:
  approvals.py — доменная логика + чистые валидаторы (без прямых commit).
  Мутации и HTTP — только в routes/manufacturing.py .

Зависимости (только read):
  api.models (Order, ManufacturingRevision, AuditLog, RevisionStatusEnum, User)
  api.access_control (enforce_factory_access)
  api.manufacturing.contracts (ManufacturingSpec для валидации)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field

from api.access_control import enforce_factory_access
from api.manufacturing.contracts import ManufacturingSpec
from api.models import (
    ManufacturingRevision,
    Order,
    RevisionStatusEnum,
    User,
)

# ============================================================================
# Enums / Decisions
# ============================================================================


class ApprovalDecision(str, Enum):
    """Решение технолога."""
    APPROVED = "approved"
    REJECTED = "rejected"


# ============================================================================
# DTOs (Pydantic) — для routes и ответов
# ============================================================================


class ApprovalRequest(BaseModel):
    """Запрос на approve/reject.

    expected_revision — optimistic concurrency.
    confirmed — явное подтверждение технолога (checkbox/фразa в UI).
    """
    expected_revision: int = Field(..., ge=1, description="Ожидаемая ревизия для OCC")
    confirmed: bool = Field(..., description="Технолог подтверждает ручную проверку и допуск к производству")
    comment: str | None = Field(None, max_length=2000)
    # confirmation_phrase может быть добавлена позже; confirmed достаточно для пилота


class ValidationIssue(BaseModel):
    """Отдельная ошибка/предупреждение с точной ссылкой на операцию."""
    code: str
    message: str
    panel_id: str | None = None
    operation_id: str | None = None
    severity: str = "error"  # error | warning


class ValidateResponse(BaseModel):
    """Результат валидации для UI технолога."""
    order_id: UUID
    revision_number: int
    spec_valid: bool
    blocking_errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    summary: str


class ApprovalResponse(BaseModel):
    """Успешный ответ approve."""
    revision_id: UUID
    decision: ApprovalDecision
    new_status: str
    revision_number: int
    order_manufacturing_status: str
    audit: dict[str, Any]


class ExportGateResponse(BaseModel):
    """Для внутреннего использования gate'ом."""
    allowed: bool
    reason: str | None = None
    revision_number: int | None = None


# ============================================================================
# Domain exceptions (маппятся в HTTP в routes)
# ============================================================================


class ApprovalError(Exception):
    """Базовая."""


class TechnologistRequiredError(ApprovalError):
    def __init__(self) -> None:
        super().__init__("Утверждение доступно только аутентифицированным технологам")


class CrossFactoryDenialError(ApprovalError):
    def __init__(self) -> None:
        super().__init__("Доступ запрещён: ревизия принадлежит другой фабрике")


class RevisionMismatchError(ApprovalError):
    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Stale revision: ожидается {expected}, текущая {actual}. "
            "Обновите данные и повторите."
        )


class NotApprovedForExportError(ApprovalError):
    def __init__(self, detail: str = "Требуется утверждённая ревизия технологом") -> None:
        self.detail = detail
        super().__init__(detail)


class RevisionNotReviewableError(ApprovalError):
    def __init__(self, status: str) -> None:
        super().__init__(f"Ревизия в статусе '{status}' не может быть утверждена (ожидается needs_review)")


class ConfirmationRequiredError(ApprovalError):
    def __init__(self) -> None:
        super().__init__("Технолог должен явно подтвердить (confirmed=true)")


# ============================================================================
# Pure validators (TDD — вызываются из тестов и routes)
# ============================================================================


def require_authenticated_technologist(user: User | None) -> User:
    """Authorization: только реальный пользователь."""
    if user is None:
        raise TechnologistRequiredError()
    return user


def enforce_tenant_isolation(order: Order, user: User) -> None:
    """Tenant isolation."""
    try:
        enforce_factory_access(order.factory_id, user.factory_id)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise CrossFactoryDenialError() from exc
        raise


def reject_stale_revision(revision: ManufacturingRevision, expected_revision: int) -> None:
    """Stale revision rejection (OCC)."""
    if revision.revision_number != expected_revision:
        raise RevisionMismatchError(expected=expected_revision, actual=revision.revision_number)


def require_technologist_confirmation(confirmed: bool) -> None:
    """Подтверждение технологом обязательно."""
    if not confirmed:
        raise ConfirmationRequiredError()


def validate_reviewable(revision: ManufacturingRevision) -> None:
    if revision.status != RevisionStatusEnum.NEEDS_REVIEW:
        raise RevisionNotReviewableError(revision.status)


def assert_approved_for_export(
    revision: ManufacturingRevision | None,
    order: Order | None,
) -> None:
    """Gate: PDF/DXF (и любой экспорт) разрешён только при approved revision.

    Вызывается из export routes. Возвращает 409 при нарушении.
    G-code routes — disabled полностью, вне этого scope.
    """
    if revision is None or order is None:
        raise NotApprovedForExportError("Нет ревизии для заказа")
    if revision.status != RevisionStatusEnum.APPROVED:
        raise NotApprovedForExportError(
            f"Ревизия {revision.revision_number} не утверждена (статус={revision.status}). "
            "Технолог должен утвердить перед экспортом PDF/DXF."
        )
    if order.approved_manufacturing_revision != revision.revision_number:
        raise NotApprovedForExportError(
            f"approved_manufacturing_revision={order.approved_manufacturing_revision} "
            f"!= current approved {revision.revision_number}"
        )


# ============================================================================
# Validation (использует контракты из Task 6 — без CAM)
# ============================================================================


def _validate_spec_dict(spec_dict: dict[str, Any]) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    """Простая + Pydantic валидация spec. Возвращает (blocking, warnings)."""
    blocking: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    try:
        spec = ManufacturingSpec.model_validate(spec_dict)
    except Exception as exc:  # Pydantic validation
        blocking.append(
            ValidationIssue(
                code="spec_invalid",
                message=f"Невалидная ManufacturingSpec: {exc}",
                severity="error",
            )
        )
        return blocking, warnings

    # Дополнительные доменные проверки (пример для пилота)
    if not spec.panels:
        blocking.append(
            ValidationIssue(code="no_panels", message="Спецификация не содержит панелей", severity="error")
        )
    for p in spec.panels:
        if p.width_mm <= 0 or p.height_mm <= 0 or p.thickness_mm <= 0:
            blocking.append(
                ValidationIssue(
                    code="bad_dimensions",
                    message=f"Некорректные размеры панели {p.panel_id}",
                    panel_id=str(p.panel_id),
                    severity="error",
                )
            )
        # Пример: операции должны иметь положительные координаты в bounds (упрощённо)
        for op in getattr(p, "operations", []) or []:
            if getattr(op, "x_mm", 0) < 0 or getattr(op, "y_mm", 0) < 0:
                blocking.append(
                    ValidationIssue(
                        code="op_out_of_bounds",
                        message=f"Операция {getattr(op, 'id', '?')} вне панели",
                        panel_id=str(p.panel_id),
                        operation_id=str(getattr(op, "id", "")),
                        severity="error",
                    )
                )

    if not blocking and len(spec.panels) > 0:
        # Пример предупреждения
        warnings.append(
            ValidationIssue(
                code="pilot_preview",
                message="Пилот: документы для ручной проверки технологом",
                severity="warning",
            )
        )

    return blocking, warnings


def validate_for_technologist(
    order_id: UUID,
    revision_number: int,
    spec_dict: dict[str, Any],
) -> ValidateResponse:
    """Возвращает результат валидации для approve gate."""
    blocking, warnings = _validate_spec_dict(spec_dict)
    spec_valid = len(blocking) == 0
    summary = (
        f"Ревизия {revision_number}: {len(blocking)} blocking, {len(warnings)} warnings"
    )
    return ValidateResponse(
        order_id=order_id,
        revision_number=revision_number,
        spec_valid=spec_valid,
        blocking_errors=blocking,
        warnings=warnings,
        summary=summary,
    )


# ============================================================================
# Audit (БЕЗ AI prompts — строго)
# ============================================================================


def build_audit_payload(
    *,
    revision_id: UUID,
    user: User,
    decision: ApprovalDecision,
    expected_revision: int,
    actual_revision: int,
    confirmed: bool,
    comment: str | None = None,
    spec_hash_value: str | None = None,
) -> dict[str, Any]:
    """Чистый audit log entry. Никогда не кладём prompt'ы."""
    return {
        "revision_id": str(revision_id),
        "user_id": str(user.id),
        "factory_id": str(user.factory_id),
        "decision": decision.value,
        "expected_revision": expected_revision,
        "actual_revision": actual_revision,
        "confirmed": confirmed,
        "comment": comment,
        "spec_hash": spec_hash_value,
        "timestamp": datetime.now(UTC).isoformat(),
        "source": "technologist_manual_approval",
    }


def compute_new_status(decision: ApprovalDecision) -> str:
    return RevisionStatusEnum.APPROVED if decision == ApprovalDecision.APPROVED else RevisionStatusEnum.REJECTED
