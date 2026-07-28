"""Доступ к production-экспорту заказа — единственная единица тарификации.

Один Order оплачивается целиком, сколько бы изделий в нём ни было. Повторные
скачивания уже оплаченной ревизии бесплатны: запись в order_export_access
выдаётся один раз и больше не тратит ни бесплатный первый заказ, ни кредиты пакета.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import OrderExportAccess, Payment
from api.settings import settings

log = logging.getLogger(__name__)

REASON_FREE_FIRST = "free_first"
REASON_PAYMENT = "payment"
REASON_PACK = "pack"
REASON_BETA = "beta"

KIND_SINGLE = "single"
KIND_PACK10 = "pack10"

STATUS_PENDING = "pending"
STATUS_SUCCEEDED = "succeeded"
STATUS_CANCELED = "canceled"


@dataclass(frozen=True)
class OrderAccess:
    """Состояние доступа к экспорту конкретного заказа."""

    access: bool
    reason: str | None
    price_rub: int
    pack_credits: int
    free_first_available: bool
    beta_free: bool


async def count_pack_credits(db: AsyncSession, factory_id: UUID) -> int:
    """Неизрасходованные заказы из купленных пакетов."""
    paid_packs = await db.scalar(
        select(func.count())
        .select_from(Payment)
        .where(
            Payment.factory_id == factory_id,
            Payment.kind == KIND_PACK10,
            Payment.status == STATUS_SUCCEEDED,
        )
    )
    spent = await db.scalar(
        select(func.count())
        .select_from(OrderExportAccess)
        .where(
            OrderExportAccess.factory_id == factory_id,
            OrderExportAccess.reason == REASON_PACK,
        )
    )
    return settings.PACK_SIZE * (paid_packs or 0) - (spent or 0)


async def is_free_first_available(db: AsyncSession, factory_id: UUID) -> bool:
    """Бесплатный заказ фабрике даётся один раз.

    Считаем только выдачи с причиной free_first: оплата заказа или покупка
    пакета не должны сжигать обещанный бесплатный первый заказ.
    """
    granted = await db.scalar(
        select(func.count())
        .select_from(OrderExportAccess)
        .where(
            OrderExportAccess.factory_id == factory_id,
            OrderExportAccess.reason == REASON_FREE_FIRST,
        )
    )
    return (granted or 0) == 0


async def _find_access(
    db: AsyncSession, order_id: UUID, factory_id: UUID
) -> OrderExportAccess | None:
    """Найти выданный доступ к заказу в пределах фабрики."""
    result = await db.execute(
        select(OrderExportAccess).where(
            OrderExportAccess.order_id == order_id,
            OrderExportAccess.factory_id == factory_id,
        )
    )
    return result.scalar_one_or_none()


async def resolve_order_access(
    db: AsyncSession, order_id: UUID, factory_id: UUID
) -> OrderAccess:
    """Текущее состояние доступа плюс доступные способы его получить.

    В бете доступ есть всегда: платить не за что, пейволл фронт не рисует.
    """
    granted = await _find_access(db, order_id, factory_id)
    credits = await count_pack_credits(db, factory_id)
    free_first = await is_free_first_available(db, factory_id)
    return OrderAccess(
        access=settings.BETA_FREE_MODE or granted is not None,
        reason=granted.reason if granted else (REASON_BETA if settings.BETA_FREE_MODE else None),
        price_rub=settings.PRICE_ORDER_RUB,
        pack_credits=max(credits, 0),
        free_first_available=free_first,
        beta_free=settings.BETA_FREE_MODE,
    )


async def grant_access(
    db: AsyncSession,
    order_id: UUID,
    factory_id: UUID,
    reason: str,
    payment_id: UUID | None = None,
) -> OrderExportAccess:
    """Идемпотентно выдать доступ. Гонка двух запросов даёт одну запись.

    Уникальный индекс по order_id — последний рубеж: при конфликте откатываем
    вложенную транзакцию и возвращаем уже существующую запись.
    """
    existing = await _find_access(db, order_id, factory_id)
    if existing is not None:
        return existing

    access = OrderExportAccess(
        order_id=order_id,
        factory_id=factory_id,
        reason=reason,
        payment_id=payment_id,
    )
    try:
        async with db.begin_nested():
            db.add(access)
    except IntegrityError:
        log.info("Доступ к заказу %s уже выдан параллельным запросом", order_id)
        existing = await _find_access(db, order_id, factory_id)
        if existing is None:
            raise
        return existing

    await db.commit()
    log.info("Выдан доступ к экспорту заказа %s (%s)", order_id, reason)
    return access


def payment_required_error(order_id: UUID) -> HTTPException:
    """402 по контракту: фронт показывает пейволл с ценой заказа."""
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "payment_required",
            "price_rub": settings.PRICE_ORDER_RUB,
            "order_id": str(order_id),
        },
    )


async def _lock_factory(db: AsyncSession, factory_id: UUID) -> None:
    """Advisory-lock на фабрику до конца транзакции.

    Без него параллельные экспорты разных заказов потратили бы один и тот же
    бесплатный первый заказ или последний кредит пакета дважды.
    """
    key = int.from_bytes(factory_id.bytes[:8], "big", signed=True)
    await db.execute(select(func.pg_advisory_xact_lock(key)))


async def ensure_export_allowed(
    db: AsyncSession, order_id: UUID, factory_id: UUID
) -> OrderExportAccess:
    """Пропустить экспорт: доступ есть, либо выдать его бесплатно/из пакета.

    Иначе — 402 с телом контракта. Повторный экспорт оплаченного заказа
    ничего не списывает: первая же ветка возвращает существующую запись.
    """
    granted = await _find_access(db, order_id, factory_id)
    if granted is not None:
        return granted

    await _lock_factory(db, factory_id)
    granted = await _find_access(db, order_id, factory_id)
    if granted is not None:
        return granted

    # Бета идёт раньше бесплатного первого: он не должен сгореть на халяве,
    # иначе после включения платной схемы фабрика останется без своей пробы.
    if settings.BETA_FREE_MODE:
        return await grant_access(db, order_id, factory_id, REASON_BETA)

    if await is_free_first_available(db, factory_id):
        return await grant_access(db, order_id, factory_id, REASON_FREE_FIRST)

    if await count_pack_credits(db, factory_id) > 0:
        return await grant_access(db, order_id, factory_id, REASON_PACK)

    raise payment_required_error(order_id)
