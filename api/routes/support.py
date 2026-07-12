"""Support incident routes — thin controller over api.support core.

POST /api/v1/support/incidents

Паттерн:
    Routes — thin controller. Вся доменная логика в api.support.
    Authorization — factory boundary check against Order/Artifact ownership
    через CAMJob relation. Нет email/Slack I/O — core функция чистая.

Зависимости:
    api.support          — create_support_incident, SupportIncidentRequest, etc.
    api.auth             — get_current_user
    api.models           — Order, Artifact, CAMJob, User
    api.database         — AsyncSession, get_db

Ограничения:
    Не модифицирует api.support, api.routers, models, frontend.
    Регистрация — явная через app.include_router(support_router).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.database import get_db
from api.models import CAMJob, Order, User
from api.support import (
    SupportIncidentError,
    SupportIncidentRequest,
    SupportIncidentResponse,
    create_support_incident,
)

support_router = APIRouter(prefix="/api/v1/support", tags=["Support"])


# ============================================================================
# Authorization helpers (read-only DB queries)
# ============================================================================


async def _load_order_or_404(
    db: AsyncSession,
    order_id: uuid.UUID,
) -> Order:
    """Load order by ID or raise 404."""
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ {order_id} не найден",
        )
    return order


async def _load_cam_job_by_artifact(
    db: AsyncSession,
    artifact_id: uuid.UUID,
) -> CAMJob:
    """Load CAMJob linking artifact to order, or raise 404."""
    stmt = select(CAMJob).where(CAMJob.artifact_id == artifact_id)
    result = await db.execute(stmt)
    cam_job = result.scalar_one_or_none()
    if cam_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Артефакт {artifact_id} не привязан ни к одной CAM-задаче",
        )
    return cam_job


def _enforce_factory_boundary(
    resource_factory_id: uuid.UUID | None,
    user_factory_id: uuid.UUID,
) -> None:
    """Raise 403 if resource has no factory ownership or belongs to a different factory.

    Ownerless resources (factory_id=None) are rejected — an explicit signed
    guest capability would be required for legitimate anonymous access.
    """
    if resource_factory_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ресурс не привязан к фабрике — обращение невозможно",
        )
    if resource_factory_id != user_factory_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к ресурсу другой фабрики",
        )


# ============================================================================
# Route
# ============================================================================


@support_router.post(
    "/incidents",
    response_model=SupportIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    req: SupportIncidentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SupportIncidentResponse:
    """Принять обращение в поддержку.

    Требования:
    - Аутентифицированный пользователь (get_current_user)
    - Если указан order_id — заказ должен принадлежать фабрике пользователя
    - Если указан artifact_id — артефакт должен быть привязан к заказу фабрики
    - Нет отправки email/Slack — только валидация + redaction + ответ
    """
    # 1. Authorization boundary: order ownership
    if req.order_id is not None:
        order = await _load_order_or_404(db, req.order_id)
        _enforce_factory_boundary(order.factory_id, user.factory_id)

    # 2. Authorization boundary: artifact → CAMJob → order ownership
    if req.artifact_id is not None:
        cam_job = await _load_cam_job_by_artifact(db, req.artifact_id)
        if cam_job.order_id is not None:
            order = await _load_order_or_404(db, cam_job.order_id)
            _enforce_factory_boundary(order.factory_id, user.factory_id)
        else:
            # CAMJob has no linked order — ownerless artifact, reject
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Артефакт не привязан к заказу — обращение невозможно",
            )

    # 3. Core processing (validation + redaction, no I/O)
    try:
        response = create_support_incident(req)
    except SupportIncidentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return response
