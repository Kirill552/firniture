"""Approval-flow end-to-end: bom/generate → manufacturing revision → approve → DXF gate.

Регрессионный тест цепочки, которая была не замкнута: UI мог рассчитать BOM,
но export gate всегда отвечал 409, потому что ревизия нигде не создавалась.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from api.database import SessionLocal
from api.models import ManufacturingRevision, Order

BOM_PARAMS = {
    "cabinet_type": "base",
    "width_mm": 800,
    "height_mm": 720,
    "depth_mm": 450,
    "material": "ЛДСП",
    "thickness_mm": 16,
    "shelf_count": 1,
    "door_count": 1,
    "drawer_count": 0,
}

DXF_PAYLOAD_PANELS = [{"name": "Боковина", "width_mm": 500.0, "height_mm": 400.0}]


@pytest.fixture(autouse=True, scope="module")
def _ensure_schema() -> None:
    """Гарантирует схему БД: test_bom_manufacturing_persistence дропает все
    таблицы в teardown, поэтому к этому файлу БД может прийти пустой."""
    import os

    from sqlalchemy import create_engine, text

    from api.database import Base

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://test_user:test_only_password@127.0.0.1:5434/furniture_ai_test",
    ).replace("+asyncpg", "+psycopg")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)
    engine.dispose()


async def _create_order(client: AsyncClient, headers: dict) -> UUID:
    resp = await client.post(
        "/api/v1/orders",
        json={"customer_ref": "revision-flow", "notes": "test"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return UUID(resp.json()["id"])


@pytest.mark.asyncio
async def test_bom_generate_creates_revision_and_approve_unlocks_export(
    authenticated_client: AsyncClient, auth_headers: dict,
):
    order_id = await _create_order(authenticated_client, auth_headers)
    payload = {**BOM_PARAMS, "order_id": str(order_id)}

    # 1. Первый расчёт → revision 1, номер возвращается в ответе
    r1 = await authenticated_client.post("/api/v1/bom/generate", json=payload, headers=auth_headers)
    assert r1.status_code == 200, r1.text
    assert r1.json()["manufacturing_revision"] == 1

    # 2. Повторный расчёт → revision 2 (approve относится к точной ревизии)
    r2 = await authenticated_client.post("/api/v1/bom/generate", json=payload, headers=auth_headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["manufacturing_revision"] == 2

    # 3. SSOT на заказе обновлён, обе ревизии сохранены
    async with SessionLocal() as db:
        order = await db.get(Order, order_id)
        assert order.manufacturing_revision == 2
        assert order.manufacturing_status == "needs_review"
        revs = (
            (await db.execute(select(ManufacturingRevision).where(ManufacturingRevision.order_id == order_id)))
            .scalars()
            .all()
        )
        assert len(revs) == 2

    # 4. Без approve export gate честно блокирует (409)
    dxf_blocked = await authenticated_client.post(
        "/api/v1/cam/dxf",
        json={"order_id": str(order_id), "panels": DXF_PAYLOAD_PANELS},
        headers=auth_headers,
    )
    assert dxf_blocked.status_code == 409

    # 5. Approve устаревшей ревизии отклоняется (409 stale)
    stale = await authenticated_client.post(
        f"/api/v1/orders/{order_id}/manufacturing/approve",
        json={"confirmed": True, "expected_revision": 1},
        headers=auth_headers,
    )
    assert stale.status_code == 409

    # 6. Approve актуальной ревизии проходит
    approved = await authenticated_client.post(
        f"/api/v1/orders/{order_id}/manufacturing/approve",
        json={"confirmed": True, "expected_revision": 2},
        headers=auth_headers,
    )
    assert approved.status_code == 200, approved.text

    # 7. После approve gate пропускает (job создаётся, а не 409)
    dxf_allowed = await authenticated_client.post(
        "/api/v1/cam/dxf",
        json={"order_id": str(order_id), "panels": DXF_PAYLOAD_PANELS},
        headers=auth_headers,
    )
    assert dxf_allowed.status_code != 409


@pytest.mark.asyncio
async def test_get_bom_exposes_revision_numbers(authenticated_client: AsyncClient, auth_headers: dict):
    """GET /orders/{id}/bom отдаёт manufacturing_revision и approved_manufacturing_revision."""
    order_id = await _create_order(authenticated_client, auth_headers)
    payload = {**BOM_PARAMS, "order_id": str(order_id)}
    r = await authenticated_client.post("/api/v1/bom/generate", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text

    bom = await authenticated_client.get(f"/api/v1/orders/{order_id}/bom", headers=auth_headers)
    assert bom.status_code == 200, bom.text
    body = bom.json()
    assert body["manufacturing_revision"] == 1
    assert body["approved_manufacturing_revision"] is None
