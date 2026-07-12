"""Интеграционные тесты manufacturing approval flow — Task 8.

POST /api/v1/manufacturing/revisions/{revision_id}/approve
POST /api/v1/manufacturing/revisions/{revision_id}/reject
GET  /api/v1/manufacturing/revisions/{revision_id}/cam-gate

Acceptance criteria:
- Focused approval flow tests pass
- Anonymous/cross-factory/stale revisions denied
- Fail closed if required schema unavailable
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.models import (
    AuditLog,
    ManufacturingRevision,
    Order,
    RevisionStatusEnum,
    User,
)
from api.routes.manufacturing import router

# ============================================================================
# Fixtures
# ============================================================================

FACTORY_A = uuid.uuid4()
FACTORY_B = uuid.uuid4()
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
ORDER_A_ID = uuid.uuid4()
REVISION_ID = uuid.uuid4()
CAM_JOB_ID = uuid.uuid4()


def _make_user(user_id: uuid.UUID, factory_id: uuid.UUID) -> User:
    """Build a lightweight User mock (no DB session needed)."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"{user_id}@test.local"
    user.factory_id = factory_id
    user.is_active = True
    user.is_owner = False
    return user


def _make_order(order_id: uuid.UUID, factory_id: uuid.UUID) -> Order:
    """Build a lightweight Order mock with factory_id for boundary checks."""
    order = MagicMock(spec=Order)
    order.id = order_id
    order.factory_id = factory_id
    order.title = "Test Order"
    return order


def _make_revision(
    revision_id: uuid.UUID,
    *,
    status: str = RevisionStatusEnum.NEEDS_REVIEW,
    revision_number: int = 1,
    order: Order | None = None,
    cam_job_id: uuid.UUID | None = None,
) -> ManufacturingRevision:
    """Build a ManufacturingRevision with the given parameters.

    Uses MagicMock to avoid SQLAlchemy instrumentation while preserving
    attribute get/set semantics the route needs (status, needs_review, etc.).
    """
    rev = MagicMock(spec=ManufacturingRevision)
    rev.id = revision_id
    rev.cam_job_id = cam_job_id
    rev.order_id = order.id if order else uuid.uuid4()
    rev.revision_number = revision_number
    rev.spec = {"panels": []}
    rev.status = status
    rev.needs_review = status == RevisionStatusEnum.NEEDS_REVIEW
    rev.provenance = {"source": "test"}
    rev.created_by = uuid.uuid4()
    rev.created_at = datetime.now(UTC)
    rev.updated_at = datetime.now(UTC)
    rev.order = order
    rev.cam_job = None
    return rev


def _mock_db_result(revision: ManufacturingRevision | None = None) -> MagicMock:
    """Create a mock SQLAlchemy result that returns the given revision."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = revision
    return result


def _make_mock_session(revision: ManufacturingRevision | None = None) -> MagicMock:
    """Create a mock DB session with correct sync/async method signatures.

    SQLAlchemy session.add() is synchronous; execute/commit/refresh/rollback
    are async.  Using MagicMock as base and patching async methods individually.
    """
    session = MagicMock()
    session.execute = AsyncMock(return_value=_mock_db_result(revision))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    # session.add() is sync — MagicMock handles it natively
    return session


@pytest.fixture
def mfg_app() -> FastAPI:
    """Create a test FastAPI app with the manufacturing router mounted."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def user_a() -> User:
    return _make_user(USER_A_ID, FACTORY_A)


@pytest.fixture
def user_b() -> User:
    return _make_user(USER_B_ID, FACTORY_B)


@pytest.fixture
def order_a() -> Order:
    return _make_order(ORDER_A_ID, FACTORY_A)


def _approve_payload(
    *,
    decision: str = "approved",
    expected_revision: int = 1,
    comment: str | None = None,
) -> dict[str, Any]:
    """Build a valid approval request body."""
    body: dict[str, Any] = {
        "decision": decision,
        "expected_revision": expected_revision,
    }
    if comment is not None:
        body["comment"] = comment
    return body


# ============================================================================
# 1. Router registration contract
# ============================================================================


class TestManufacturingRouterRegistration:
    """Explicit registration contract — router is importable and has correct endpoints."""

    def test_router_has_approve_endpoint(self):
        routes = {r.path for r in router.routes}
        assert "/api/v1/manufacturing/revisions/{revision_id}/approve" in routes

    def test_router_has_reject_endpoint(self):
        routes = {r.path for r in router.routes}
        assert "/api/v1/manufacturing/revisions/{revision_id}/reject" in routes

    def test_router_has_cam_gate_endpoint(self):
        routes = {r.path for r in router.routes}
        assert "/api/v1/manufacturing/revisions/{revision_id}/cam-gate" in routes

    def test_router_prefix(self):
        assert router.prefix == "/api/v1/manufacturing"


# ============================================================================
# 2. Authentication required — anonymous denied
# ============================================================================


class TestManufacturingAuthentication:
    """Unauthenticated requests are rejected."""

    @pytest.mark.asyncio
    async def test_approve_no_auth_returns_401(self, mfg_app: FastAPI):
        """POST /approve without auth → 401."""
        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(),
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_reject_no_auth_returns_401(self, mfg_app: FastAPI):
        """POST /reject without auth → 401."""
        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/reject",
                json=_approve_payload(decision="rejected"),
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_cam_gate_no_auth_returns_401(self, mfg_app: FastAPI):
        """GET /cam-gate without auth → 401."""
        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/cam-gate",
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_approve_none_user_returns_401(self, mfg_app: FastAPI, user_a: User):
        """POST /approve with dependency returning None user → 401."""

        async def _no_user():
            return None

        from api.auth import get_current_user

        mfg_app.dependency_overrides[get_current_user] = _no_user

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(),
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 3. Schema unavailable → fail closed
# ============================================================================


class TestManufacturingFailClosed:
    """When required schema is unavailable, route fails closed."""

    @pytest.mark.asyncio
    async def test_approve_missing_body_returns_422(self, mfg_app: FastAPI, user_a: User):
        """POST /approve without body → 422 (schema validation)."""
        from api.auth import get_current_user

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
            )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_missing_expected_revision_returns_422(
        self, mfg_app: FastAPI, user_a: User
    ):
        """POST /approve without expected_revision → 422 (required field)."""
        from api.auth import get_current_user

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json={"decision": "approved"},
            )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_invalid_decision_returns_422(
        self, mfg_app: FastAPI, user_a: User
    ):
        """POST /approve with invalid decision → 422."""
        from api.auth import get_current_user

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json={"decision": "INVALID", "expected_revision": 1},
            )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_expected_revision_zero_returns_422(
        self, mfg_app: FastAPI, user_a: User
    ):
        """POST /approve with expected_revision=0 → 422 (ge=1 constraint)."""
        from api.auth import get_current_user

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json={"decision": "approved", "expected_revision": 0},
            )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 4. Happy path — approval and rejection
# ============================================================================


class TestManufacturingApprovalHappyPath:
    """Successful approval/rejection flow."""

    @pytest.mark.asyncio
    async def test_approve_needs_review_revision(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve on needs_review revision → 200 with approved status."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["decision"] == "approved"
        assert body["new_status"] == "approved"
        assert body["revision_number"] == 1
        assert body["revision_id"] == str(REVISION_ID)
        assert body["audit"]["decision"] == "approved"
        assert body["audit"]["expected_revision"] == 1
        assert body["audit"]["actual_revision"] == 1
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_reject_needs_review_revision(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /reject forces decision=REJECTED → 200 with rejected status."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/reject",
                json=_approve_payload(decision="approved", expected_revision=1),
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["decision"] == "rejected"
        assert body["new_status"] == "rejected"
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_persists_audit_log(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve creates an AuditLog entry in the session."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_200_OK
        # Verify db.add was called (at least twice: revision + audit_log)
        assert session.add.call_count >= 2
        # Verify db.commit was called
        session.commit.assert_awaited_once()
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_with_comment(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve with comment → audit includes the comment."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1, comment="LGTM"),
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["audit"]["comment"] == "LGTM"
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_revision_not_found_returns_404(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve for non-existent revision → 404."""
        from api.auth import get_current_user
        from api.database import get_db

        session = _make_mock_session(revision=None)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 5. Optimistic concurrency — stale revision denied
# ============================================================================


class TestManufacturingOptimisticConcurrency:
    """Stale revision (expected_revision mismatch) → 409 Conflict."""

    @pytest.mark.asyncio
    async def test_stale_revision_returns_409(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve with expected_revision=1 on revision_number=2 → 409."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID, order=order_a, revision_number=2
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_409_CONFLICT
        body = resp.json()
        assert "error" in body["detail"]
        assert body["detail"]["error"] == "revision_mismatch"
        assert body["detail"]["expected"] == 1
        assert body["detail"]["actual"] == 2
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_stale_revision_rollback_on_409(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """On 409, session is rolled back — no stale writes."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID, order=order_a, revision_number=5
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=3),
            )

        assert resp.status_code == status.HTTP_409_CONFLICT
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 6. Cross-factory boundary — foreign factory denied
# ============================================================================


class TestManufacturingCrossFactoryBoundary:
    """Each factory can only approve their own revisions."""

    @pytest.mark.asyncio
    async def test_cross_factory_approve_returns_403(
        self, mfg_app: FastAPI, user_b: User, order_a: Order
    ):
        """User from factory B tries to approve revision belonging to factory A → 403."""
        from api.auth import get_current_user
        from api.database import get_db

        # order_a has FACTORY_A; user_b has FACTORY_B
        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_b
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        session.commit.assert_not_awaited()
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_same_factory_approve_succeeds(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """User from factory A can approve revision belonging to factory A → 200."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_200_OK
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 7. Status gates — non-reviewable revision denied
# ============================================================================


class TestManufacturingStatusGates:
    """Revisions not in needs_review status cannot be approved/rejected."""

    @pytest.mark.asyncio
    async def test_approve_already_approved_returns_400(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve on already-approved revision → 400."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID,
            status=RevisionStatusEnum.APPROVED,
            order=order_a,
            revision_number=1,
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        session.commit.assert_not_awaited()
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_rejected_revision_returns_400(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve on rejected revision → 400."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID,
            status=RevisionStatusEnum.REJECTED,
            order=order_a,
            revision_number=1,
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_approve_draft_revision_returns_400(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve on draft revision → 400."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID,
            status=RevisionStatusEnum.DRAFT,
            order=order_a,
            revision_number=1,
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 8. CAM gate — only approved revisions pass
# ============================================================================


class TestManufacturingCAMGate:
    """CAM gate checks: approved → pass, others → fail."""

    @pytest.mark.asyncio
    async def test_cam_gate_approved_passes(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """GET /cam-gate on approved revision → gate_passed=True."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID,
            status=RevisionStatusEnum.APPROVED,
            order=order_a,
            revision_number=1,
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/cam-gate",
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["gate_passed"] is True
        assert body["revision_status"] == "approved"
        assert body["revision_id"] == str(REVISION_ID)
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cam_gate_needs_review_fails(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """GET /cam-gate on needs_review revision → gate_passed=False."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/cam-gate",
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["gate_passed"] is False
        assert body["revision_status"] == "needs_review"
        assert body["reason"] is not None
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cam_gate_rejected_fails(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """GET /cam-gate on rejected revision → gate_passed=False."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID,
            status=RevisionStatusEnum.REJECTED,
            order=order_a,
            revision_number=1,
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/cam-gate",
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["gate_passed"] is False
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cam_gate_not_found_returns_404(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """GET /cam-gate for non-existent revision → 404."""
        from api.auth import get_current_user
        from api.database import get_db

        session = _make_mock_session(revision=None)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/cam-gate",
            )

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cam_gate_cross_factory_returns_403(
        self, mfg_app: FastAPI, user_b: User, order_a: Order
    ):
        """GET /cam-gate from wrong factory → 403."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(
            REVISION_ID,
            status=RevisionStatusEnum.APPROVED,
            order=order_a,
            revision_number=1,
        )
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_b
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/cam-gate",
            )

        assert resp.status_code == status.HTTP_403_FORBIDDEN
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 9. Audit trail — no AI prompts in audit
# ============================================================================


class TestManufacturingAuditTrailIntegrity:
    """Audit entries contain no AI prompt content."""

    @pytest.mark.asyncio
    async def test_audit_no_ai_prompt_fields(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """POST /approve → audit response has no AI prompt or system prompt fields."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(
                    expected_revision=1,
                    comment="No AI prompts here",
                ),
            )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        audit = body["audit"]

        # Audit contains only expected fields — no AI artifacts
        expected_keys = {
            "revision_id",
            "user_id",
            "factory_id",
            "decision",
            "expected_revision",
            "actual_revision",
            "comment",
            "timestamp",
            "metadata",
        }
        assert set(audit.keys()) == expected_keys
        assert audit["comment"] == "No AI prompts here"
        # Comment is the only text — no prompt payloads leaked
        mfg_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_audit_log_actor_role_is_technologist(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """Persisted AuditLog has actor_role='technologist'."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_200_OK

        # Inspect the AuditLog passed to db.add
        calls = session.add.call_args_list
        audit_log_calls = [
            c for c in calls if isinstance(c[0][0], AuditLog)
        ]
        assert len(audit_log_calls) == 1
        audit_log: AuditLog = audit_log_calls[0][0][0]
        assert audit_log.actor_role == "technologist"
        assert audit_log.action == "revision_approved"
        assert audit_log.entity == "manufacturing_revision"
        assert audit_log.entity_id == REVISION_ID
        assert "factory_id" in audit_log.details
        assert "user_id" in audit_log.details
        mfg_app.dependency_overrides.clear()


# ============================================================================
# 10. Revision mutation — needs_review cleared on decision
# ============================================================================


class TestManufacturingRevisionMutation:
    """Approved/rejected revision has needs_review=False."""

    @pytest.mark.asyncio
    async def test_approve_clears_needs_review(
        self, mfg_app: FastAPI, user_a: User, order_a: Order
    ):
        """After approval, revision.needs_review is set to False."""
        from api.auth import get_current_user
        from api.database import get_db

        revision = _make_revision(REVISION_ID, order=order_a, revision_number=1)
        assert revision.needs_review is True

        session = _make_mock_session(revision)

        mfg_app.dependency_overrides[get_current_user] = lambda: user_a
        mfg_app.dependency_overrides[get_db] = lambda: session

        transport = ASGITransport(app=mfg_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/manufacturing/revisions/{REVISION_ID}/approve",
                json=_approve_payload(expected_revision=1),
            )

        assert resp.status_code == status.HTTP_200_OK
        # Revision was mutated in-memory
        assert revision.needs_review is False
        assert revision.status == "approved"
        mfg_app.dependency_overrides.clear()
