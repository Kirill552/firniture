"""Контракты HTTP-слоя платежей. Единица тарификации — один заказ."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CheckoutResponse(BaseModel):
    """Ответ обоих checkout-эндпоинтов."""

    payment_id: UUID = Field(description="ID платежа в нашей БД")
    confirmation_url: str = Field(description="Страница оплаты ЮKassa")
    amount_rub: int = Field(description="Сумма к оплате в рублях")
    status: str = Field(description="pending | succeeded | canceled")


class PackCheckoutRequest(BaseModel):
    """Тело оплаты пакета. Необязательно: нужно только для возврата на заказ."""

    order_id: UUID | None = Field(
        default=None, description="Заказ, из которого пользователь ушёл платить"
    )


class OrderAccessResponse(BaseModel):
    """Состояние доступа к экспорту конкретного заказа."""

    access: bool
    reason: str | None = Field(description="free_first | payment | pack | beta | null")
    price_rub: int
    pack_credits: int
    free_first_available: bool
    beta_free: bool = Field(default=False, description="Бета: экспорт бесплатен, пейволл скрыт")


class BalanceResponse(BaseModel):
    """Баланс фабрики: сколько заказов оплачено вперёд и почём."""

    pack_credits: int
    free_first_available: bool
    price_rub: int
    pack_price_rub: int
    pack_size: int
    beta_free: bool = Field(default=False, description="Бета: оплата отключена")


class WebhookAck(BaseModel):
    """Подтверждение приёма уведомления ЮKassa."""

    ok: bool = True
