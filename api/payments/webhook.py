"""Приём уведомлений ЮKassa.

Тело уведомления недоверенное: берём из него только `object.id`, а фактический
статус запрашиваем у API ЮKassa. Ответ фронтенда на успех платежа ни на что не
влияет — деньги засчитываются только здесь. Повторная доставка того же
уведомления ничего не дублирует.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import Payment
from api.payments.access import (
    KIND_SINGLE,
    REASON_PAYMENT,
    STATUS_CANCELED,
    STATUS_SUCCEEDED,
    grant_access,
)
from api.payments.schemas import WebhookAck
from api.payments.yookassa_client import YooKassaClient, YooKassaError, get_yookassa_client

log = logging.getLogger(__name__)

# Префикс задаёт родительский payments_router, поэтому здесь только хвост пути.
webhook_router = APIRouter()

_BAD_BODY = "Некорректное тело уведомления"


async def _read_notification_payment_id(request: Request) -> str:
    """Достать object.id из тела уведомления. Мусор — 400 без стектрейса."""
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_BAD_BODY) from None

    obj = body.get("object") if isinstance(body, dict) else None
    remote_id = obj.get("id") if isinstance(obj, dict) else None
    if not isinstance(remote_id, str) or not remote_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_BAD_BODY)
    return remote_id


async def _apply_confirmed_status(
    db: AsyncSession, payment: Payment, remote_status: str
) -> None:
    """Применить статус, подтверждённый API ЮKassa, и выдать доступ."""
    if remote_status == STATUS_CANCELED:
        payment.status = STATUS_CANCELED
        await db.commit()
        return

    if remote_status != STATUS_SUCCEEDED:
        return

    payment.status = STATUS_SUCCEEDED
    payment.paid_at = payment.paid_at or datetime.utcnow()
    await db.commit()

    if payment.kind == KIND_SINGLE and payment.order_id is not None:
        await grant_access(
            db, payment.order_id, payment.factory_id, REASON_PAYMENT, payment_id=payment.id
        )


@webhook_router.post("/webhook/yookassa", response_model=WebhookAck)
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: YooKassaClient = Depends(get_yookassa_client),
) -> WebhookAck:
    """Уведомление ЮKassa. Без авторизации — ЮKassa её не присылает."""
    remote_id = await _read_notification_payment_id(request)

    result = await db.execute(select(Payment).where(Payment.yookassa_payment_id == remote_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        log.warning("Уведомление о неизвестном платеже %s — игнорируем", remote_id)
        return WebhookAck()

    if payment.status == STATUS_SUCCEEDED:
        return WebhookAck()

    try:
        remote = await client.get_payment(remote_id)
    except YooKassaError as exc:
        log.warning("Не удалось проверить платёж %s: %s", remote_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Платёжный сервис недоступен"
        ) from exc

    await _apply_confirmed_status(db, payment, str(remote.get("status") or ""))
    return WebhookAck()
