"""Денежный контур: бесплатный первый заказ, оплата 890 ₽, пакет из 10.

Сеть к ЮKassa замокана целиком: клиент подменяется через dependency_overrides,
а conftest дополнительно блокирует сокеты. Реальных вызовов ЮKassa нет.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select

from api.auth import get_current_user
from api.crud import create_manufacturing_revision
from api.database import SessionLocal
from api.main import app
from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
from api.models import Factory, Order, OrderExportAccess, Payment, RevisionStatusEnum, User
from api.payments.access import (
    count_pack_credits,
    ensure_export_allowed,
    grant_access,
)
from api.payments.yookassa_client import get_yookassa_client

PANELS = [{"name": "Боковина", "width_mm": 500.0, "height_mm": 400.0}]
PRICE_RUB = 890
PACK_PRICE_RUB = 7900


class FakeYooKassa:
    """Заглушка ЮKassa: помнит созданные платежи и отдаёт заданный статус."""

    def __init__(self) -> None:
        self.statuses: dict[str, str] = {}
        self.get_calls = 0
        self.return_urls: list[str] = []

    async def create_payment(
        self, amount_rub, description, return_url, metadata, idempotence_key
    ) -> dict:
        remote_id = f"yk-{uuid.uuid4().hex[:12]}"
        self.statuses[remote_id] = "pending"
        self.return_urls.append(return_url)
        return {
            "id": remote_id,
            "status": "pending",
            "confirmation": {"type": "redirect", "confirmation_url": f"https://pay.test/{remote_id}"},
        }

    async def get_payment(self, payment_id: str) -> dict:
        self.get_calls += 1
        return {"id": payment_id, "status": self.statuses.get(payment_id, "pending")}


@pytest_asyncio.fixture
async def tenant(client: AsyncClient) -> AsyncIterator[tuple[AsyncClient, User, FakeYooKassa]]:
    """Свежая фабрика без истории: бесплатный первый заказ ещё не потрачен."""
    factory_id, user_id = uuid.uuid4(), uuid.uuid4()
    user = User(id=user_id, email=f"{user_id}@example.com", factory_id=factory_id, is_owner=True)

    async with SessionLocal() as db:
        db.add(Factory(id=factory_id, name="Payments Factory"))
        db.add(User(id=user_id, email=user.email, factory_id=factory_id, is_owner=True))
        await db.commit()

    fake = FakeYooKassa()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_yookassa_client] = lambda: fake
    yield client, user, fake
    app.dependency_overrides.clear()


async def _new_order(factory_id: UUID) -> UUID:
    """Заказ фабрики напрямую в БД — без прогона всего пайплайна."""
    order_id = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Order(id=order_id, factory_id=factory_id, customer_ref="pay-test"))
        await db.commit()
    return order_id


async def _approved_order(factory_id: UUID) -> UUID:
    """Заказ с утверждённой ревизией — экспорт упрётся только в пейволл."""
    order_id = await _new_order(factory_id)
    spec = ManufacturingSpec(
        panels=[PanelSpec(id="p1", width_mm=500.0, height_mm=400.0, thickness_mm=16.0)]
    )
    async with SessionLocal() as db:
        rev = await create_manufacturing_revision(db, order_id, spec, provenance={"source": "test"})
        rev.status = RevisionStatusEnum.APPROVED
        order = await db.get(Order, order_id)
        order.manufacturing_status = "approved"
        order.approved_manufacturing_revision = rev.revision_number
        await db.commit()
    return order_id


async def _access_rows(order_id: UUID) -> list[OrderExportAccess]:
    async with SessionLocal() as db:
        result = await db.execute(
            select(OrderExportAccess).where(OrderExportAccess.order_id == order_id)
        )
        return list(result.scalars().all())


async def _credits(factory_id: UUID) -> int:
    async with SessionLocal() as db:
        return await count_pack_credits(db, factory_id)


@pytest.mark.asyncio
async def test_first_export_free_second_requires_payment(tenant) -> None:
    """Первый заказ фабрики бесплатен, второй отдаёт 402 с телом контракта."""
    http, user, _ = tenant
    first = await _approved_order(user.factory_id)
    second = await _approved_order(user.factory_id)

    free = await http.post("/api/v1/cam/dxf", json={"order_id": str(first), "panels": PANELS})
    assert free.status_code == 200, free.text

    paywalled = await http.post("/api/v1/cam/dxf", json={"order_id": str(second), "panels": PANELS})
    assert paywalled.status_code == 402
    assert paywalled.json()["detail"] == {
        "code": "payment_required",
        "price_rub": PRICE_RUB,
        "order_id": str(second),
    }


@pytest.mark.asyncio
async def test_paid_order_does_not_burn_free_first(tenant) -> None:
    """Оплата заказа не сжигает обещанный бесплатный первый заказ."""
    http, user, _ = tenant
    paid = await _approved_order(user.factory_id)
    async with SessionLocal() as db:
        await grant_access(db, paid, user.factory_id, "payment")

    balance = await http.get("/api/v1/payments/balance")
    assert balance.json()["free_first_available"] is True

    other = await _approved_order(user.factory_id)
    export = await http.post("/api/v1/cam/dxf", json={"order_id": str(other), "panels": PANELS})
    assert export.status_code == 200, export.text

    rows = await _access_rows(other)
    assert [row.reason for row in rows] == ["free_first"]


@pytest.mark.asyncio
async def test_checkout_conflicts_when_access_already_granted(tenant) -> None:
    """Оплачивать открытый заказ нечего — 409."""
    http, user, _ = tenant
    order_id = await _approved_order(user.factory_id)
    async with SessionLocal() as db:
        await grant_access(db, order_id, user.factory_id, "free_first")

    resp = await http.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_webhook_grants_access_exactly_once_for_two_deliveries(tenant) -> None:
    """Повторная доставка того же уведомления не дублирует доступ."""
    http, user, fake = tenant
    burned = await _new_order(user.factory_id)
    async with SessionLocal() as db:
        await grant_access(db, burned, user.factory_id, "free_first")

    order_id = await _approved_order(user.factory_id)
    checkout = await http.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["amount_rub"] == PRICE_RUB
    assert checkout.json()["status"] == "pending"

    async with SessionLocal() as db:
        payment = await db.get(Payment, UUID(checkout.json()["payment_id"]))
        remote_id = payment.yookassa_payment_id
    fake.statuses[remote_id] = "succeeded"

    body = {"type": "notification", "event": "payment.succeeded", "object": {"id": remote_id}}
    for _ in range(2):
        delivery = await http.post("/api/v1/payments/webhook/yookassa", json=body)
        assert delivery.status_code == 200
        assert delivery.json() == {"ok": True}

    rows = await _access_rows(order_id)
    assert len(rows) == 1
    assert rows[0].reason == "payment"
    assert fake.get_calls == 1, "второе уведомление не должно ходить в ЮKassa повторно"

    export = await http.post("/api/v1/cam/dxf", json={"order_id": str(order_id), "panels": PANELS})
    assert export.status_code == 200, export.text


@pytest.mark.asyncio
async def test_webhook_ignores_untrusted_body_status(tenant) -> None:
    """Статус из тела уведомления не засчитывается: ЮKassa говорит pending."""
    http, user, fake = tenant
    order_id = await _new_order(user.factory_id)
    async with SessionLocal() as db:
        await grant_access(db, await _new_order(user.factory_id), user.factory_id, "free_first")

    checkout = await http.post(f"/api/v1/payments/orders/{order_id}/checkout")
    async with SessionLocal() as db:
        payment = await db.get(Payment, UUID(checkout.json()["payment_id"]))
        remote_id = payment.yookassa_payment_id

    body = {"type": "notification", "event": "payment.succeeded", "object": {"id": remote_id}}
    assert (await http.post("/api/v1/payments/webhook/yookassa", json=body)).status_code == 200
    assert await _access_rows(order_id) == []


@pytest.mark.asyncio
async def test_webhook_rejects_garbage_body(tenant) -> None:
    """Мусорное тело — 400, без падения обработчика."""
    http, _, _ = tenant
    assert (await http.post("/api/v1/payments/webhook/yookassa", json={"x": 1})).status_code == 400
    assert (
        await http.post(
            "/api/v1/payments/webhook/yookassa",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
    ).status_code == 400


@pytest.mark.asyncio
async def test_pack_gives_ten_exports_and_eleventh_requires_payment(tenant) -> None:
    """Пакет — ровно 10 списаний, одиннадцатое требует оплаты."""
    http, user, fake = tenant
    async with SessionLocal() as db:
        await grant_access(db, await _new_order(user.factory_id), user.factory_id, "free_first")

    checkout = await http.post("/api/v1/payments/packs/checkout")
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["amount_rub"] == PACK_PRICE_RUB

    async with SessionLocal() as db:
        payment = await db.get(Payment, UUID(checkout.json()["payment_id"]))
        remote_id = payment.yookassa_payment_id
    fake.statuses[remote_id] = "succeeded"
    body = {"type": "notification", "event": "payment.succeeded", "object": {"id": remote_id}}
    assert (await http.post("/api/v1/payments/webhook/yookassa", json=body)).status_code == 200

    balance = (await http.get("/api/v1/payments/balance")).json()
    assert balance == {
        "pack_credits": 10,
        "free_first_available": False,
        "price_rub": PRICE_RUB,
        "pack_price_rub": PACK_PRICE_RUB,
        "pack_size": 10,
    }

    for index in range(10):
        order_id = await _new_order(user.factory_id)
        async with SessionLocal() as db:
            granted = await ensure_export_allowed(db, order_id, user.factory_id)
        assert granted.reason == "pack", f"списание {index + 1} должно идти из пакета"

    assert await _credits(user.factory_id) == 0
    extra = await _new_order(user.factory_id)
    async with SessionLocal() as db:
        with pytest.raises(Exception) as exc:
            await ensure_export_allowed(db, extra, user.factory_id)
    assert exc.value.status_code == 402
    assert exc.value.detail["order_id"] == str(extra)


@pytest.mark.asyncio
async def test_repeated_export_of_paid_order_spends_nothing(tenant) -> None:
    """Повторное скачивание оплаченного заказа не тратит кредит пакета."""
    http, user, fake = tenant
    async with SessionLocal() as db:
        await grant_access(db, await _new_order(user.factory_id), user.factory_id, "free_first")

    checkout = await http.post("/api/v1/payments/packs/checkout")
    async with SessionLocal() as db:
        payment = await db.get(Payment, UUID(checkout.json()["payment_id"]))
        remote_id = payment.yookassa_payment_id
    fake.statuses[remote_id] = "succeeded"
    await http.post(
        "/api/v1/payments/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": remote_id}},
    )

    order_id = await _approved_order(user.factory_id)
    for _ in range(3):
        resp = await http.post("/api/v1/cam/dxf", json={"order_id": str(order_id), "panels": PANELS})
        assert resp.status_code == 200, resp.text

    assert await _credits(user.factory_id) == 9
    assert len(await _access_rows(order_id)) == 1
    state = (await http.get(f"/api/v1/payments/orders/{order_id}/access")).json()
    assert state == {
        "access": True,
        "reason": "pack",
        "price_rub": PRICE_RUB,
        "pack_credits": 9,
        "free_first_available": False,
    }


@pytest.mark.asyncio
async def test_foreign_factory_gets_no_access_from_someone_elses_payment(tenant) -> None:
    """Оплата одной фабрики не открывает экспорт другой."""
    http, payer, fake = tenant
    async with SessionLocal() as db:
        await grant_access(db, await _new_order(payer.factory_id), payer.factory_id, "free_first")

    paid_order = await _new_order(payer.factory_id)
    checkout = await http.post(f"/api/v1/payments/orders/{paid_order}/checkout")
    async with SessionLocal() as db:
        payment = await db.get(Payment, UUID(checkout.json()["payment_id"]))
        remote_id = payment.yookassa_payment_id
    fake.statuses[remote_id] = "succeeded"
    await http.post(
        "/api/v1/payments/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": remote_id}},
    )

    stranger_factory, stranger_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Factory(id=stranger_factory, name="Stranger"))
        db.add(User(id=stranger_id, email=f"{stranger_id}@example.com", factory_id=stranger_factory))
        await db.commit()
    stranger = User(id=stranger_id, email=f"{stranger_id}@x", factory_id=stranger_factory)
    app.dependency_overrides[get_current_user] = lambda: stranger

    foreign_view = await http.get(f"/api/v1/payments/orders/{paid_order}/access")
    assert foreign_view.status_code == 403

    async with SessionLocal() as db:
        used_up = await _new_order(stranger_factory)
        await grant_access(db, used_up, stranger_factory, "free_first")
        own_order = await _new_order(stranger_factory)
        with pytest.raises(Exception) as exc:
            await ensure_export_allowed(db, own_order, stranger_factory)
    assert exc.value.status_code == 402

    async with SessionLocal() as db:
        leaked = await db.scalar(
            select(func.count())
            .select_from(OrderExportAccess)
            .where(OrderExportAccess.factory_id == stranger_factory)
        )
    assert leaked == 1, "чужой платёж не должен добавлять доступов"
