"""Роуты приёма платежей ЮKassa. Тонкий контроллер над api.payments.access.

Единица тарификации — один заказ целиком. Пакет из 10 заказов пополняет
кредиты фабрики; кредиты не сгорают.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.access_control import enforce_factory_access
from api.auth import get_current_user
from api.database import get_db
from api.models import Order, Payment, User
from api.payments.access import (
    KIND_PACK10,
    KIND_SINGLE,
    STATUS_PENDING,
    count_pack_credits,
    is_free_first_available,
    resolve_order_access,
)
from api.payments.schemas import (
    BalanceResponse,
    CheckoutResponse,
    OrderAccessResponse,
    PackCheckoutRequest,
)
from api.payments.webhook import webhook_router
from api.payments.yookassa_client import (
    YooKassaClient,
    YooKassaError,
    get_yookassa_client,
    new_idempotence_key,
)
from api.settings import settings

log = logging.getLogger(__name__)

payments_router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


def _return_url(order_id: UUID | None, marker: str) -> str:
    """Куда ЮKassa вернёт пользователя. Фронт читает заказ из `orderId`."""
    base = settings.YOOKASSA_RETURN_URL or f"{settings.FRONTEND_URL}/bom"
    if order_id is None:
        return f"{base}?payment={marker}"
    return f"{base}?orderId={order_id}&payment={marker}"


async def _load_own_order(db: AsyncSession, order_id: UUID, user: User) -> Order:
    """Заказ своей фабрики или 404/403."""
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    enforce_factory_access(order.factory_id, user.factory_id)
    return order


async def _start_payment(
    db: AsyncSession,
    client: YooKassaClient,
    payment: Payment,
    description: str,
    return_url: str,
    metadata: dict[str, str],
) -> CheckoutResponse:
    """Сохранить платёж, создать его в ЮKassa и отдать ссылку на оплату."""
    db.add(payment)
    await db.flush()

    try:
        remote = await client.create_payment(
            amount_rub=int(payment.amount_rub),
            description=description,
            return_url=return_url,
            metadata=metadata,
            idempotence_key=payment.idempotence_key,
        )
    except YooKassaError as exc:
        await db.rollback()
        log.warning("Не удалось создать платёж в ЮKassa: %s", exc)
        if client.is_mock:
            # Ключи магазина не заданы: честно говорим, что оплата ещё не включена
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Оплата подключается. Напишите нам — выдадим доступ вручную",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Платёжный сервис недоступен"
        ) from exc

    payment.yookassa_payment_id = remote.get("id")
    payment.status = remote.get("status") or STATUS_PENDING
    await db.commit()

    confirmation = remote.get("confirmation") or {}
    return CheckoutResponse(
        payment_id=payment.id,
        confirmation_url=confirmation.get("confirmation_url", ""),
        amount_rub=int(payment.amount_rub),
        status=payment.status,
    )


@payments_router.post("/orders/{order_id}/checkout", response_model=CheckoutResponse)
async def checkout_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client: YooKassaClient = Depends(get_yookassa_client),
) -> CheckoutResponse:
    """Оплатить один заказ целиком. 409, если доступ уже есть."""
    await _load_own_order(db, order_id, current_user)

    state = await resolve_order_access(db, order_id, current_user.factory_id)
    if state.access:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Доступ к заказу уже открыт"
        )

    payment = Payment(
        factory_id=current_user.factory_id,
        user_id=current_user.id,
        order_id=order_id,
        kind=KIND_SINGLE,
        amount_rub=settings.PRICE_ORDER_RUB,
        status=STATUS_PENDING,
        idempotence_key=new_idempotence_key(),
    )
    return await _start_payment(
        db,
        client,
        payment,
        description=f"Раскрой заказа {order_id}",
        return_url=_return_url(order_id, "success"),
        metadata={"kind": KIND_SINGLE, "order_id": str(order_id)},
    )


@payments_router.post("/packs/checkout", response_model=CheckoutResponse)
async def checkout_pack(
    body: PackCheckoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client: YooKassaClient = Depends(get_yookassa_client),
) -> CheckoutResponse:
    """Купить пакет из 10 заказов. Кредиты не сгорают."""
    payment = Payment(
        factory_id=current_user.factory_id,
        user_id=current_user.id,
        order_id=None,
        kind=KIND_PACK10,
        amount_rub=settings.PRICE_PACK10_RUB,
        status=STATUS_PENDING,
        idempotence_key=new_idempotence_key(),
    )
    return await _start_payment(
        db,
        client,
        payment,
        description=f"Пакет {settings.PACK_SIZE} заказов АвтоРаскрой",
        return_url=_return_url(body.order_id if body else None, "pack"),
        metadata={"kind": KIND_PACK10, "factory_id": str(current_user.factory_id)},
    )


@payments_router.get("/orders/{order_id}/access", response_model=OrderAccessResponse)
async def get_order_access(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderAccessResponse:
    """Есть ли доступ к экспорту заказа и чем его можно открыть."""
    await _load_own_order(db, order_id, current_user)
    state = await resolve_order_access(db, order_id, current_user.factory_id)
    return OrderAccessResponse(
        access=state.access,
        reason=state.reason,
        price_rub=state.price_rub,
        pack_credits=state.pack_credits,
        free_first_available=state.free_first_available,
    )


@payments_router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BalanceResponse:
    """Сколько заказов у фабрики оплачено вперёд и почём следующий."""
    credits = await count_pack_credits(db, current_user.factory_id)
    return BalanceResponse(
        pack_credits=max(credits, 0),
        free_first_available=await is_free_first_available(db, current_user.factory_id),
        price_rub=settings.PRICE_ORDER_RUB,
        pack_price_rub=settings.PRICE_PACK10_RUB,
        pack_size=settings.PACK_SIZE,
    )


payments_router.include_router(webhook_router)
