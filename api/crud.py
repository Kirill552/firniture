from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.manufacturing.contracts import ManufacturingSpec
from api.manufacturing.coordinates import spec_hash

from . import models, schemas
from .models import ProductConfig


async def create_order(
    db: AsyncSession,
    order: schemas.OrderCreate,
    factory_id: UUID | None = None,
    created_by_id: UUID | None = None
) -> models.Order:
    """Создать новый заказ с привязкой к фабрике."""
    db_order = models.Order(
        **order.dict(),
        factory_id=factory_id,
        created_by_id=created_by_id
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order


async def get_orders_by_factory(
    db: AsyncSession,
    factory_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> list[models.Order]:
    """Получить заказы фабрики с пагинацией."""
    stmt = (
        select(models.Order)
        .where(models.Order.factory_id == factory_id)
        .order_by(models.Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_order_with_history(db: AsyncSession, order_id: UUID) -> models.Order | None:
    """Получить заказ и историю его диалога."""
    stmt = (
        select(models.Order)
        .where(models.Order.id == order_id)
        .options(selectinload(models.Order.dialogue_messages))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_dialogue_message(
    db: AsyncSession,
    order_id: UUID,
    turn_number: int,
    role: str,
    content: str
) -> models.DialogueMessage:
    """Создать новое сообщение в диалоге."""
    db_message = models.DialogueMessage(
        order_id=order_id,
        turn_number=turn_number,
        role=role,
        content=content
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message


async def get_order_with_products(db: AsyncSession, order_id: UUID) -> models.Order | None:
    """Получить заказ с его изделиями и панелями."""
    stmt = (
        select(models.Order)
        .where(models.Order.id == order_id)
        .options(
            selectinload(models.Order.products).selectinload(models.ProductConfig.panels)
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def finalize_order(
    db: AsyncSession,
    order_id: UUID,
    spec,
) -> ProductConfig:
    """
    Финализирует заказ: создаёт ProductConfig с собранными параметрами.
    Обновляет статус заказа на 'ready'.
    """
    # Получаем заказ и обновляем статус
    order = await db.get(models.Order, order_id)
    if order:
        order.status = "ready"

    # Создаём ProductConfig
    product = ProductConfig(
        order_id=order_id,
        name=spec.furniture_type,
        width_mm=spec.dimensions.width_mm,
        height_mm=spec.dimensions.height_mm,
        depth_mm=spec.dimensions.depth_mm,
        material=spec.body_material.type if spec.body_material else None,
        thickness_mm=spec.body_material.thickness_mm if spec.body_material else None,
        params={
            "furniture_type": spec.furniture_type,
            "body_material": spec.body_material.model_dump() if spec.body_material else None,
            "facade_material": spec.facade_material.model_dump() if spec.facade_material else None,
            "hardware": [h.model_dump() for h in spec.hardware],
            "edge_band": spec.edge_band,
            "door_count": spec.door_count,
            "drawer_count": spec.drawer_count,
            "shelf_count": spec.shelf_count,
        },
        notes=spec.notes,
    )
    db.add(product)
    await db.flush()

    return product


async def update_order_status(db: AsyncSession, order_id: UUID, status: str) -> models.Order | None:
    """Обновить статус заказа."""
    order = await db.get(models.Order, order_id)
    if order:
        order.status = status
        await db.commit()
        await db.refresh(order)
    return order


async def get_dashboard_stats(db: AsyncSession, factory_id: UUID | None = None) -> dict:
    """
    Получить статистику заказов по статусам для dashboard.
    Если factory_id указан — только для этой фабрики.
    """
    from sqlalchemy import func

    base_query = select(models.Order.status, func.count(models.Order.id))

    if factory_id:
        base_query = base_query.where(models.Order.factory_id == factory_id)

    base_query = base_query.group_by(models.Order.status)

    result = await db.execute(base_query)
    stats = dict(result.all())

    return {
        "draft": stats.get("draft", 0),
        "ready": stats.get("ready", 0),
        "completed": stats.get("completed", 0),
        "total": sum(stats.values()),
    }

# ============================================================================
# Manufacturing Revision persistence (Task 7)
# ============================================================================

# Errors ----------------------------------------------------------------


class RevisionConflictError(Exception):
    """Raised when expected_revision does not match current revision_number."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"expected_revision {expected} != current {actual} — 409 Conflict"
        )


# CRUD -------------------------------------------------------------------


async def create_manufacturing_revision(
    db: AsyncSession,
    order_id: UUID,
    spec: ManufacturingSpec,
    *,
    provenance: dict | None = None,
    created_by: UUID | None = None,
) -> models.ManufacturingRevision:
    """Persist a complete ManufacturingSpec as a new revision.

    The ``spec`` is serialised to its canonical JSON form and stored in the
    ``spec`` column.  A ``spec_hash`` is embedded in ``provenance`` so that
    downstream consumers can verify integrity without re-serialising.
    """
    h = spec_hash(spec)
    prov = dict(provenance or {})
    prov["spec_hash"] = h

    # Determine next revision number for this order
    result = await db.execute(
        select(models.ManufacturingRevision)
        .where(models.ManufacturingRevision.order_id == order_id)
        .order_by(models.ManufacturingRevision.revision_number.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    next_number = (last.revision_number + 1) if last else 1

    rev = models.ManufacturingRevision(
        order_id=order_id,
        revision_number=next_number,
        spec=spec.to_canonical_dict(),
        status=models.RevisionStatusEnum.NEEDS_REVIEW,
        needs_review=True,
        provenance=prov,
        created_by=created_by,
    )
    db.add(rev)
    await db.commit()
    await db.refresh(rev)
    return rev


async def get_manufacturing_revision(
    db: AsyncSession,
    revision_id: UUID,
) -> models.ManufacturingRevision | None:
    """Load a manufacturing revision by ID."""
    result = await db.execute(
        select(models.ManufacturingRevision).where(
            models.ManufacturingRevision.id == revision_id
        )
    )
    return result.scalar_one_or_none()


async def get_latest_revision_for_order(
    db: AsyncSession,
    order_id: UUID,
) -> models.ManufacturingRevision | None:
    """Load the most recent revision for an order (by revision_number)."""
    result = await db.execute(
        select(models.ManufacturingRevision)
        .where(models.ManufacturingRevision.order_id == order_id)
        .order_by(models.ManufacturingRevision.revision_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_manufacturing_revision(
    db: AsyncSession,
    revision_id: UUID,
    spec: ManufacturingSpec,
    expected_revision: int,
    *,
    updated_by: UUID | None = None,
) -> models.ManufacturingRevision:
    """Update an existing revision's spec with optimistic concurrency.

    Raises ``RevisionConflictError`` when ``expected_revision`` does not match
    the stored ``revision_number`` (maps to HTTP 409).

    On successful update the revision's status is reset to ``needs_review``
    and the approval/artifact provenance is invalidated.
    """
    rev = await get_manufacturing_revision(db, revision_id)
    if rev is None:
        raise LookupError(f"revision {revision_id} not found")
    if rev.revision_number != expected_revision:
        raise RevisionConflictError(expected_revision, rev.revision_number)

    h = spec_hash(spec)
    rev.spec = spec.to_canonical_dict()
    rev.status = models.RevisionStatusEnum.NEEDS_REVIEW
    rev.needs_review = True
    prov = dict(rev.provenance or {})
    prov["spec_hash"] = h
    prov["invalidated_by_edit"] = True
    if updated_by:
        prov["last_edited_by"] = str(updated_by)
    rev.provenance = prov
    rev.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rev)
    return rev


async def list_manufacturing_revisions(
    db: AsyncSession,
    order_id: UUID,
) -> list[models.ManufacturingRevision]:
    """Return all revisions for an order, newest first."""
    result = await db.execute(
        select(models.ManufacturingRevision)
        .where(models.ManufacturingRevision.order_id == order_id)
        .order_by(models.ManufacturingRevision.revision_number.desc())
    )
    return list(result.scalars().all())
