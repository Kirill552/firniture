from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


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
