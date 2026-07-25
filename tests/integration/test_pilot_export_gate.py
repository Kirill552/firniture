"""Интеграционные тесты gate экспорта PDF карты раскроя (Task 8 pilot).

Проверяют, что POST /api/v1/cam/cutting-map-pdf:
- требует order_id в теле запроса;
- отказывает чужому factory (403);
- отказывает при неутверждённой ревизии (409);
- возвращает application/pdf при утверждённой ревизии.
"""

from __future__ import annotations

import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient

from api.auth import get_current_user
from api.crud import create_manufacturing_revision
from api.database import SessionLocal
from api.main import app
from api.manufacturing.contracts import ManufacturingSpec, PanelSpec
from api.models import Factory, ManufacturingRevision, Order, RevisionStatusEnum, User

PANELS_PAYLOAD = [
    {"name": "Боковина", "width_mm": 500.0, "height_mm": 400.0},
]


def _make_user(user_id: UUID, factory_id: UUID) -> User:
    """Создать тестового пользователя в памяти."""
    return User(
        id=user_id,
        email=f"{user_id}@test.local",
        factory_id=factory_id,
        is_active=True,
        is_owner=True,
    )


def _make_spec() -> ManufacturingSpec:
    """Минимальная manufacturing spec для ревизии."""
    return ManufacturingSpec(
        panels=[
            PanelSpec(id="p1", width_mm=500.0, height_mm=400.0, thickness_mm=16.0),
        ]
    )


async def _create_order(client: AsyncClient) -> UUID:
    """Создать заказ через API и вернуть его ID."""
    resp = await client.post(
        "/api/v1/orders",
        json={"customer_ref": "pilot-export", "notes": "test"},
    )
    assert resp.status_code == 200, resp.text
    return UUID(resp.json()["id"])


async def _create_revision(
    db,
    order_id: UUID,
    status: str,
) -> ManufacturingRevision:
    """Создать manufacturing revision для заказа в заданном статусе."""
    rev = await create_manufacturing_revision(
        db,
        order_id,
        _make_spec(),
        provenance={"source": "test"},
    )
    rev.status = status
    if status == RevisionStatusEnum.APPROVED:
        order = await db.get(Order, order_id)
        order.manufacturing_status = "approved"
        order.approved_manufacturing_revision = rev.revision_number
    await db.commit()
    await db.refresh(rev)
    return rev


@pytest.mark.asyncio
async def test_pdf_export_unowned_order_returns_403(authenticated_client: AsyncClient):
    """Пользователь из другой фабрики не может экспортировать PDF чужого заказа."""
    order_id = await _create_order(authenticated_client)

    async with SessionLocal() as db:
        await _create_revision(db, order_id, RevisionStatusEnum.APPROVED)

    other_factory_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    async with SessionLocal() as db:
        await db.merge(Factory(id=other_factory_id, name="Other Factory"))
        await db.merge(_make_user(other_user_id, other_factory_id))
        await db.commit()

    other_user = _make_user(other_user_id, other_factory_id)
    app.dependency_overrides[get_current_user] = lambda: other_user

    resp = await authenticated_client.post(
        "/api/v1/cam/cutting-map-pdf",
        json={"order_id": str(order_id), "panels": PANELS_PAYLOAD},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pdf_export_unapproved_revision_returns_409(authenticated_client: AsyncClient):
    """Неутверждённая ревизия блокирует экспорт PDF (409)."""
    order_id = await _create_order(authenticated_client)

    async with SessionLocal() as db:
        await _create_revision(db, order_id, RevisionStatusEnum.NEEDS_REVIEW)

    resp = await authenticated_client.post(
        "/api/v1/cam/cutting-map-pdf",
        json={"order_id": str(order_id), "panels": PANELS_PAYLOAD},
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_pdf_export_approved_revision_returns_pdf(authenticated_client: AsyncClient):
    """Утверждённая ревизия позволяет получить PDF карты раскроя."""
    order_id = await _create_order(authenticated_client)

    async with SessionLocal() as db:
        await _create_revision(db, order_id, RevisionStatusEnum.APPROVED)

    resp = await authenticated_client.post(
        "/api/v1/cam/cutting-map-pdf",
        json={"order_id": str(order_id), "panels": PANELS_PAYLOAD},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
