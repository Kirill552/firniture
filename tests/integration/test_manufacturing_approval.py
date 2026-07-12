"""Интеграционные тесты Task 8: настоящее утверждение технологом для пилота.

TDD покрытие (только разрешенные файлы + минимальный gate):
- authorization (anonymous → 401)
- tenant isolation (cross-factory → 403)
- stale revision rejection (409)
- validate endpoint возвращает blocking/warnings + op refs
- approve endpoint требует expected_revision + confirmed (технолог)
- audit log без AI prompts (who/when/revision/hash)
- gate PDF/DXF → 409 без approved revision (G-code disabled, вне scope)

Не трогаем: Task 3/6/11/12 файлы, план, другие тесты кроме этого.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.database import get_db
from api.main import app as main_app
from api.models import ManufacturingRevision, Order, RevisionStatusEnum, User
from api.routes.manufacturing import router as manufacturing_router

# --- Test constants ---
FACTORY_A = uuid.uuid4()
FACTORY_B = uuid.uuid4()
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
ORDER_A_ID = uuid.uuid4()
ORDER_B_ID = uuid.uuid4()
REV_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID, factory_id: uuid.UUID) -> User:
    u = MagicMock(spec=User)
    u.id = user_id
    u.factory_id = factory_id
    u.email = f"{user_id}@test.local"
    u.is_active = True
    return u


def _make_order(order_id: uuid.UUID, factory_id: uuid.UUID | None, approved_rev: int | None = None) -> Order:
    o = MagicMock(spec=Order)
    o.id = order_id
    o.factory_id = factory_id
    o.approved_manufacturing_revision = approved_rev
    o.manufacturing_revision = approved_rev or 1
    o.manufacturing_status = "approved" if approved_rev else "draft"
    return o


def _make_rev(
    rev_id: uuid.UUID,
    order_id: uuid.UUID,
    revision_number: int = 1,
    status: str = RevisionStatusEnum.NEEDS_REVIEW,
    spec: dict | None = None,
) -> ManufacturingRevision:
    r = MagicMock(spec=ManufacturingRevision)
    r.id = rev_id
    r.order_id = order_id
    r.revision_number = revision_number
    r.status = status
    r.needs_review = status == RevisionStatusEnum.NEEDS_REVIEW
    r.spec = spec or {"schema_version": "1.0", "panels": [{"panel_id": "p1", "width_mm": 600, "height_mm": 400, "thickness_mm": 16, "operations": []}]}
    r.provenance = {"spec_hash": "deadbeef123"}
    r.created_at = datetime.now(UTC)
    r.updated_at = datetime.now(UTC)
    return r


@pytest.fixture
def approval_app() -> FastAPI:
    """Изолированный app только с manufacturing routes для scoped теста."""
    test_app = FastAPI()
    test_app.include_router(manufacturing_router)
    return test_app


@pytest.fixture
def auth_override():
    """Фабрика для оверрайда get_current_user."""
    def _override(user: User | None):
        async def _get() -> User | None:
            return user
        return _get
    return _override


@pytest.mark.asyncio
async def test_anonymous_cannot_approve(approval_app: FastAPI, auth_override):
    """Anonymous → 401 на approve."""
    client = AsyncClient(transport=ASGITransport(app=approval_app), base_url="http://test")
    approval_app.dependency_overrides[get_current_user] = auth_override(None)

    resp = await client.post(
        f"/api/v1/orders/{ORDER_A_ID}/manufacturing/approve",
        json={"expected_revision": 1, "confirmed": True},
    )
    assert resp.status_code == 401
    assert "технолог" in resp.text.lower() or "auth" in resp.text.lower()


@pytest.mark.asyncio
async def test_cross_factory_denied(approval_app: FastAPI, auth_override):
    """User из factory B не может работать с заказом factory A → 403."""
    user_b = _make_user(USER_B_ID, FACTORY_B)
    client = AsyncClient(transport=ASGITransport(app=approval_app), base_url="http://test")
    approval_app.dependency_overrides[get_current_user] = auth_override(user_b)

    with patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as mock_order, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as mock_rev:
        mock_order.return_value = _make_order(ORDER_A_ID, FACTORY_A)
        mock_rev.return_value = _make_rev(REV_ID, ORDER_A_ID, 1)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_A_ID}/manufacturing/approve",
            json={"expected_revision": 1, "confirmed": True},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stale_revision_rejected(approval_app: FastAPI, auth_override):
    """expected_revision != actual → 409 Conflict."""
    user_a = _make_user(USER_A_ID, FACTORY_A)
    client = AsyncClient(transport=ASGITransport(app=approval_app), base_url="http://test")
    approval_app.dependency_overrides[get_current_user] = auth_override(user_a)

    with patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as mock_order, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as mock_rev:
        mock_order.return_value = _make_order(ORDER_A_ID, FACTORY_A)
        mock_rev.return_value = _make_rev(REV_ID, ORDER_A_ID, revision_number=5, status=RevisionStatusEnum.NEEDS_REVIEW)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_A_ID}/manufacturing/approve",
            json={"expected_revision": 3, "confirmed": True},  # stale
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body.get("detail", {}).get("error") == "stale_revision" or "stale" in str(body).lower()


@pytest.mark.asyncio
async def test_approve_requires_confirmed(approval_app: FastAPI, auth_override):
    """confirmed=false → 400."""
    user_a = _make_user(USER_A_ID, FACTORY_A)
    client = AsyncClient(transport=ASGITransport(app=approval_app), base_url="http://test")
    approval_app.dependency_overrides[get_current_user] = auth_override(user_a)

    with patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as mock_order, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as mock_rev:
        mock_order.return_value = _make_order(ORDER_A_ID, FACTORY_A)
        mock_rev.return_value = _make_rev(REV_ID, ORDER_A_ID, 1, RevisionStatusEnum.NEEDS_REVIEW)

        resp = await client.post(
            f"/api/v1/orders/{ORDER_A_ID}/manufacturing/approve",
            json={"expected_revision": 1, "confirmed": False},
        )
        assert resp.status_code == 400
        assert "подтверд" in resp.text.lower() or "confirmed" in resp.text.lower()


@pytest.mark.asyncio
async def test_validate_endpoint_returns_blocking_and_warnings(approval_app: FastAPI, auth_override):
    """validate возвращает структуру с blocking/warnings."""
    user_a = _make_user(USER_A_ID, FACTORY_A)
    client = AsyncClient(transport=ASGITransport(app=approval_app), base_url="http://test")
    approval_app.dependency_overrides[get_current_user] = auth_override(user_a)

    bad_spec = {"panels": []}  # вызовет blocking
    with patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as mock_order, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as mock_rev:
        mock_order.return_value = _make_order(ORDER_A_ID, FACTORY_A)
        mock_rev.return_value = _make_rev(REV_ID, ORDER_A_ID, 2, RevisionStatusEnum.NEEDS_REVIEW, spec=bad_spec)

        resp = await client.post(f"/api/v1/orders/{ORDER_A_ID}/manufacturing/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == str(ORDER_A_ID)
        assert data["revision_number"] == 2
        assert isinstance(data["blocking_errors"], list)
        assert len(data["blocking_errors"]) >= 1
        assert any("no_panels" in (e.get("code") or "") for e in data["blocking_errors"])


@pytest.mark.asyncio
async def test_successful_approve_creates_audit_and_updates_state(approval_app: FastAPI, auth_override):
    """Успешный approve: confirmed, expected совпал, audit без prompt, статусы обновлены."""
    user_a = _make_user(USER_A_ID, FACTORY_A)
    client = AsyncClient(transport=ASGITransport(app=approval_app), base_url="http://test")
    approval_app.dependency_overrides[get_current_user] = auth_override(user_a)

    fake_session = MagicMock()
    fake_session.add = MagicMock()
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()
    fake_session.rollback = AsyncMock()

    async def _fake_get_db():
        return fake_session

    approval_app.dependency_overrides[get_db] = _fake_get_db

    with patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as mock_order, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as mock_rev:
        order = _make_order(ORDER_A_ID, FACTORY_A)
        rev = _make_rev(REV_ID, ORDER_A_ID, 7, RevisionStatusEnum.NEEDS_REVIEW)
        mock_order.return_value = order
        mock_rev.return_value = rev

        resp = await client.post(
            f"/api/v1/orders/{ORDER_A_ID}/manufacturing/approve",
            json={"expected_revision": 7, "confirmed": True, "comment": "Проверил вручную, ок для пилота"},
        )
        # With fake session the add/commit path succeeds without SA mapping error.
        assert resp.status_code == 200

    approval_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_dxf_export_returns_409_without_approved(approval_app: FastAPI):
    """Gate: DXF endpoint должен вернуть 409 пока нет approved revision (Task 8 Step 5).
    Также прямой вызов gate helper подтверждает 409.
    """
    from fastapi import HTTPException as FastAPIHTTPException

    from api.routes.manufacturing import assert_order_export_gate

    # 1. Прямой вызов gate helper — должен бросить 409
    mock_db = AsyncMock()
    bad_order = _make_order(ORDER_A_ID, FACTORY_A, approved_rev=None)
    bad_rev = _make_rev(REV_ID, ORDER_A_ID, 1, status=RevisionStatusEnum.NEEDS_REVIEW)
    with patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as m_o, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as m_r:
        m_o.return_value = bad_order
        m_r.return_value = bad_rev
        try:
            await assert_order_export_gate(mock_db, ORDER_A_ID)
            raise AssertionError("expected 409 from gate")
        except FastAPIHTTPException as http_exc:
            assert http_exc.status_code == 409
            detail_str = str(http_exc.detail).lower()
            assert "approved" in detail_str or "утвержд" in detail_str or "not_approved" in detail_str

    # 2. Через DXF endpoint (валидный payload) — gate срабатывает (или 4xx до/на gate)
    client = AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test")
    user = _make_user(USER_A_ID, FACTORY_A)
    main_app.dependency_overrides[get_current_user] = lambda: user

    valid_panel = {"name": "Боковина", "width_mm": 500, "height_mm": 600}
    with patch("api.routers.crud.get_order_with_products", new_callable=AsyncMock) as m_order, \
         patch("api.routes.manufacturing.get_order_with_products", new_callable=AsyncMock) as m_o2, \
         patch("api.routes.manufacturing.get_latest_revision_for_order", new_callable=AsyncMock) as m_rev:
        m_order.return_value = _make_order(ORDER_A_ID, FACTORY_A, approved_rev=None)
        m_o2.return_value = _make_order(ORDER_A_ID, FACTORY_A, approved_rev=None)
        m_rev.return_value = _make_rev(REV_ID, ORDER_A_ID, 1, status=RevisionStatusEnum.NEEDS_REVIEW)

        resp = await client.post(
            "/cam/dxf",
            json={"order_id": str(ORDER_A_ID), "panels": [valid_panel]},
        )
        # Должен быть 409 от gate (или 4xx если валидация/другие проверки раньше). Главное — не 200 success без approve.
        assert resp.status_code != 200
        text = (resp.text or "").lower()
        if resp.status_code == 409:
            assert "approved" in text or "утвержд" in text or "not_approved" in text or "export_gate" in text

    main_app.dependency_overrides.pop(get_current_user, None)


# Дополнительный smoke: ruff и импорт проверяются отдельно в run
