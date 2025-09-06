from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


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
