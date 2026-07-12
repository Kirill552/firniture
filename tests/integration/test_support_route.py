"""Интеграционные тесты support route — POST /api/v1/support/incidents.

Проверяет:
- Регистрация роутера (explicit contract — роутер импортируется, include_router работает)
- Аутентификация required
- Authorization boundary: order/factory ownership
- Authorization boundary: artifact → CAMJob → order → factory ownership
- Response contract: redacted_description, no raw secrets
- 422 на отсутствие both order_id и artifact_id
- No email/Slack I/O в route code

Ограничения:
- Не модифицирует api.support, api.routers, models, frontend.
- Все DB-запросы мокаются через FastAPI dependency_overrides.
- Нет browser, нет network.
"""

from __future__ import annotations

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.auth import get_current_user
from api.database import get_db
from api.models import CAMJob, Order, User
from api.routes.support import support_router

# ============================================================================
# Fixtures: test app with support router
# ============================================================================

FACTORY_A = uuid.uuid4()
FACTORY_B = uuid.uuid4()
USER_A_ID = uuid.uuid4()
ORDER_A_ID = uuid.uuid4()
ORDER_B_ID = uuid.uuid4()
ARTIFACT_A_ID = uuid.uuid4()


def _make_user(factory_id: uuid.UUID) -> User:
    """Build a lightweight User mock (no DB session needed)."""
    user = MagicMock(spec=User)
    user.id = USER_A_ID
    user.factory_id = factory_id
    return user


def _make_order(order_id: uuid.UUID, factory_id: uuid.UUID | None) -> Order:
    """Build a lightweight Order mock."""
    order = MagicMock(spec=Order)
    order.id = order_id
    order.factory_id = factory_id
    return order


def _make_cam_job(order_id: uuid.UUID | None, artifact_id: uuid.UUID) -> CAMJob:
    """Build a lightweight CAMJob mock."""
    cam_job = MagicMock(spec=CAMJob)
    cam_job.order_id = order_id
    cam_job.artifact_id = artifact_id
    return cam_job


@pytest.fixture
def support_app() -> FastAPI:
    """Create a test FastAPI app with the support router mounted."""
    app = FastAPI()
    app.include_router(support_router)
    return app


@pytest.fixture
def user_a() -> User:
    return _make_user(FACTORY_A)


@pytest.fixture
def user_b() -> User:
    return _make_user(FACTORY_B)


# ============================================================================
# 1. Router registration contract
# ============================================================================


class TestSupportRouterRegistration:
    """Explicit registration contract — router is importable and has the right endpoint."""

    def test_router_exists_and_has_prefix(self) -> None:
        """Router is importable, has expected prefix."""
        assert support_router.prefix == "/api/v1/support"
        assert support_router.tags == ["Support"]

    def test_router_has_incidents_endpoint(self) -> None:
        """Router exposes POST /incidents."""
        routes = {r.path: r.methods for r in support_router.routes}
        assert "/api/v1/support/incidents" in routes
        assert "POST" in routes["/api/v1/support/incidents"]

    def test_router_can_be_included(self, support_app: FastAPI) -> None:
        """include_router works without error."""
        # If we got here, support_app fixture succeeded.
        routes = {r.path for r in support_app.routes}
        assert "/api/v1/support/incidents" in routes

    def test_route_is_not_registered_in_main_app(self) -> None:
        """Support router is NOT auto-registered in api.main.app.

        Registration must be explicit — this test documents the deferred
        registration contract. When ready, add:
            from api.routes.support import support_router
            app.include_router(support_router)
        to api/main.py.
        """
        from api.main import app

        routes = {r.path for r in app.routes}
        assert "/api/v1/support/incidents" not in routes


# ============================================================================
# 2. Authentication required
# ============================================================================


class TestSupportAuthentication:
    """Unauthenticated requests are rejected."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, support_app: FastAPI) -> None:
        """No auth header → 401/403 from get_current_user."""
        # Override get_current_user to raise (simulating no auth)
        async def _no_auth():
            from fastapi import HTTPException
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        support_app.dependency_overrides[get_current_user] = _no_auth

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "category": "technical",
                    "description": "Станок не запускается после обновления прошивки",
                    "contact_email": "ivan@example.com",
                },
            )
        assert resp.status_code in (401, 403)


# ============================================================================
# 3. Authorization boundary — order ownership
# ============================================================================


class TestSupportOrderAuthorization:
    """Order ownership boundary: same factory → allowed, different/missing → 403."""

    @pytest.mark.asyncio
    async def test_same_factory_order_accepted(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """User from factory A → order belonging to factory A → 201."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_A_ID, FACTORY_A)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "category": "technical",
                    "description": "Станок не запускается после обновления прошивки",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["status"] == "received"
        assert body["category"] == "technical"
        assert body["incident_id"].startswith("INC-")

    @pytest.mark.asyncio
    async def test_cross_factory_order_rejected(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """User from factory A → order belonging to factory B → 403."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_B_ID, FACTORY_B)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_B_ID),
                    "category": "billing",
                    "description": "Вопрос по оплате последнего заказа на фабрику",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_order_not_found_returns_404(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Non-existent order_id → 404."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # order not found
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(uuid.uuid4()),
                    "category": "technical",
                    "description": "Не могу найти свой заказ в системе",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_anonymous_order_rejected(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Order with factory_id=None (ownerless) is rejected — 403."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_A_ID, None)  # ownerless order
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "category": "other",
                    "description": "Обращение по анонимному заказу без фабрики",
                    "contact_email": "anon@example.com",
                },
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# 4. Authorization boundary — artifact ownership
# ============================================================================


class TestSupportArtifactAuthorization:
    """Artifact → CAMJob → Order → factory ownership boundary."""

    @pytest.mark.asyncio
    async def test_same_factory_artifact_accepted(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Artifact linked to factory A's order → 201."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_cam_job = _make_cam_job(ORDER_A_ID, ARTIFACT_A_ID)
        mock_order = _make_order(ORDER_A_ID, FACTORY_A)

        mock_db = AsyncMock()
        # First call: CAMJob query, second call: Order query
        cam_result = MagicMock()
        cam_result.scalar_one_or_none.return_value = mock_cam_job
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.side_effect = [cam_result, order_result]
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "artifact_id": str(ARTIFACT_A_ID),
                    "category": "technical",
                    "description": "Артефакт CAM-задачи повреждён или некорректен",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_cross_factory_artifact_rejected(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Artifact linked to factory B's order → 403."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_cam_job = _make_cam_job(ORDER_B_ID, ARTIFACT_A_ID)
        mock_order = _make_order(ORDER_B_ID, FACTORY_B)

        mock_db = AsyncMock()
        cam_result = MagicMock()
        cam_result.scalar_one_or_none.return_value = mock_cam_job
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.side_effect = [cam_result, order_result]
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "artifact_id": str(ARTIFACT_A_ID),
                    "category": "technical",
                    "description": "Артефакт CAM-задачи повреждён или некорректен",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_artifact_not_linked_returns_404(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Artifact with no CAMJob link → 404."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # no CAMJob
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "artifact_id": str(uuid.uuid4()),
                    "category": "technical",
                    "description": "Артефакт не найден в системе CAM-задач",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_ownerless_artifact_rejected(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Artifact whose CAMJob has no linked order → 403 (ownerless, no boundary)."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_cam_job = _make_cam_job(None, ARTIFACT_A_ID)  # order_id=None

        mock_db = AsyncMock()
        cam_result = MagicMock()
        cam_result.scalar_one_or_none.return_value = mock_cam_job
        mock_db.execute.return_value = cam_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "artifact_id": str(ARTIFACT_A_ID),
                    "category": "technical",
                    "description": "Артефакт CAM-задачи без привязки к заказу",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# 5. Response contract — no leakage
# ============================================================================


class TestSupportResponseContract:
    """Response contains no raw description, no secrets, no email/Slack."""

    @pytest.mark.asyncio
    async def test_response_has_no_raw_description(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Response contains redacted_description, NOT the raw input."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_A_ID, FACTORY_A)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        secret_text = "Мой ключ sk-abc123def456ghi789jkl012mno сломался"
        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "category": "technical",
                    "description": secret_text,
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        # Redacted description contains no raw secret
        assert "sk-abc123def456ghi789jkl012mno" not in body["redacted_description"]
        assert "[REDACTED_SECRET]" in body["redacted_description"]

    @pytest.mark.asyncio
    async def test_response_has_required_fields(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Response contract: incident_id, status, category, redacted_description, created_at."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_A_ID, FACTORY_A)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "category": "feature_request",
                    "description": "Хотелось бы добавить экспорт спецификации в PDF формат",
                    "contact_email": "manager@example.com",
                    "contact_name": "Менеджер Ольга",
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert "incident_id" in body
        assert "status" in body
        assert "category" in body
        assert "redacted_description" in body
        assert "created_at" in body
        assert body["category"] == "feature_request"
        assert body["status"] == "received"

    @pytest.mark.asyncio
    async def test_response_excludes_original_description(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Original (unredacted) description is never in the response."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_A_ID, FACTORY_A)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "category": "technical",
                    "description": "Проблема. Email: admin@secret.com. Тел: +7 999 123 45 67",
                    "contact_email": "user@example.com",
                },
            )

        body = resp.json()
        # Raw email and phone must be absent from response
        assert "admin@secret.com" not in body["redacted_description"]
        assert "+7 999 123 45 67" not in body["redacted_description"]
        assert "[REDACTED_EMAIL]" in body["redacted_description"]
        assert "[REDACTED_PHONE]" in body["redacted_description"]


# ============================================================================
# 6. Validation — missing both IDs
# ============================================================================


class TestSupportValidation:
    """Request validation: missing both order_id and artifact_id → 422."""

    @pytest.mark.asyncio
    async def test_missing_both_ids_returns_422(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Neither order_id nor artifact_id → 422 (core validation)."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a
        support_app.dependency_overrides[get_db] = lambda: AsyncMock()

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "category": "other",
                    "description": "Обращение без привязки к заказу или артефакту",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = resp.json()
        assert "хотя бы один" in body["detail"]


# ============================================================================
# 7. No email/Slack I/O in route code
# ============================================================================


class TestSupportNoIO:
    """Route module contains no email/Slack/external service imports."""

    def test_route_has_no_email_imports(self) -> None:
        """Route module does not import smtplib, httpx for sending, or Slack."""
        import api.routes.support as route_mod

        source = inspect.getsource(route_mod)
        # Check import lines only (not docstrings mentioning "Slack" as non-goal)
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        import_text = "\n".join(import_lines)
        assert "smtplib" not in import_text
        assert "send_email" not in import_text
        assert "send_magic_link" not in import_text
        assert "slack" not in import_text.lower()
        assert "requests.post" not in import_text
        assert "httpx.AsyncClient" not in import_text

    def test_route_has_no_db_writes(self) -> None:
        """Route module does not call db.add(), db.commit(), or db.delete()."""
        import api.routes.support as route_mod

        source = inspect.getsource(route_mod)
        assert "db.add(" not in source
        assert "db.commit(" not in source
        assert "db.delete(" not in source


# ============================================================================
# 8. Both order_id and artifact_id simultaneously
# ============================================================================


class TestSupportBothIdentifiers:
    """Both order_id and artifact_id provided — both boundaries enforced."""

    @pytest.mark.asyncio
    async def test_both_ids_same_factory_accepted(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Both order and artifact belong to factory A → 201."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order = _make_order(ORDER_A_ID, FACTORY_A)
        mock_cam_job = _make_cam_job(ORDER_A_ID, ARTIFACT_A_ID)

        mock_db = AsyncMock()
        # First call: order lookup, second: CAMJob lookup, third: order lookup for artifact
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = mock_order
        cam_result = MagicMock()
        cam_result.scalar_one_or_none.return_value = mock_cam_job
        mock_db.execute.side_effect = [order_result, cam_result, order_result]
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "artifact_id": str(ARTIFACT_A_ID),
                    "category": "technical",
                    "description": "Обращение по заказу и артефакту одной фабрики",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_cross_factory_order_and_artifact_rejected(
        self, support_app: FastAPI, user_a: User
    ) -> None:
        """Order from factory A, artifact linked to factory B's order → 403."""
        support_app.dependency_overrides[get_current_user] = lambda: user_a

        mock_order_a = _make_order(ORDER_A_ID, FACTORY_A)
        mock_cam_job_b = _make_cam_job(ORDER_B_ID, ARTIFACT_A_ID)
        mock_order_b = _make_order(ORDER_B_ID, FACTORY_B)

        mock_db = AsyncMock()
        # 1st call: order lookup (factory A), 2nd: CAMJob lookup, 3rd: order lookup (factory B)
        order_a_result = MagicMock()
        order_a_result.scalar_one_or_none.return_value = mock_order_a
        cam_result = MagicMock()
        cam_result.scalar_one_or_none.return_value = mock_cam_job_b
        order_b_result = MagicMock()
        order_b_result.scalar_one_or_none.return_value = mock_order_b
        mock_db.execute.side_effect = [order_a_result, cam_result, order_b_result]
        support_app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=support_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/support/incidents",
                json={
                    "order_id": str(ORDER_A_ID),
                    "artifact_id": str(ARTIFACT_A_ID),
                    "category": "technical",
                    "description": "Заказ фабрики A, артефакт из CAM-задачи фабрики B",
                    "contact_email": "ivan@example.com",
                },
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
