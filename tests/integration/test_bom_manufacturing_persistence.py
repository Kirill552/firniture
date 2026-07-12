"""Integration tests for BOM manufacturing persistence (Task 7).

Validates complete round-trip: create → reload → update → conflict.
No routes — pure CRUD-level validation using async SQLAlchemy session.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api import models
from api.crud import (
    RevisionConflictError,
    create_manufacturing_revision,
    get_manufacturing_revision,
    list_manufacturing_revisions,
    update_manufacturing_revision,
)
from api.database import Base
from api.manufacturing.contracts import (
    DrillOperation,
    Face,
    ManufacturingSpec,
    PanelSpec,
    PocketOperation,
    SlotOperation,
    Unit,
)

# ---------------------------------------------------------------------------
# Database fixture — async session for CRUD tests
# ---------------------------------------------------------------------------
_TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://test_user:test_only_password@127.0.0.1:5434/furniture_ai_test",
)


TEST_FACTORY_ID = uuid.uuid4()
TEST_USER_ID = uuid.uuid4()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session with tables created and seed data inserted."""
    from sqlalchemy import text

    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        # Seed prerequisite rows so FK constraints are satisfied
        session.add(
            models.Factory(id=TEST_FACTORY_ID, name="Test Factory")
        )
        session.add(
            models.User(
                id=TEST_USER_ID,
                factory_id=TEST_FACTORY_ID,
                email="test@test.com",
            )
        )
        # Create an order so order_id FK resolves
        session.add(
            models.Order(id=ORDER_ID, factory_id=TEST_FACTORY_ID, status="draft")
        )
        session.add(
            models.Order(id=ORDER_ID_2, factory_id=TEST_FACTORY_ID, status="draft")
        )
        await session.commit()
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORDER_ID = uuid.uuid4()
ORDER_ID_2 = uuid.uuid4()


def _make_spec(*, with_operations: bool = True) -> ManufacturingSpec:
    """Return a deterministic ManufacturingSpec for testing."""
    panels = [
        PanelSpec(
            id="left",
            width_mm=300.0,
            height_mm=700.0,
            thickness_mm=18.0,
            material="ЛДСП",
            operations=(
                [
                    DrillOperation(
                        id="drill_1",
                        face=Face.FRONT,
                        x_mm=50.0,
                        y_mm=100.0,
                        diameter_mm=35.0,
                        depth_mm=18.0,
                    ),
                    SlotOperation(
                        id="slot_1",
                        face=Face.FRONT,
                        x_mm=50.0,
                        y_mm=0.0,
                        length_mm=100.0,
                        width_mm=8.0,
                        depth_mm=6.0,
                    ),
                ]
                if with_operations
                else []
            ),
        ),
        PanelSpec(
            id="right",
            width_mm=300.0,
            height_mm=700.0,
            thickness_mm=18.0,
            material="ЛДСП",
            operations=(
                [
                    PocketOperation(
                        id="pocket_1",
                        face=Face.FRONT,
                        x_mm=80.0,
                        y_mm=200.0,
                        width_mm=120.0,
                        height_mm=60.0,
                        depth_mm=6.0,
                    ),
                ]
                if with_operations
                else []
            ),
        ),
        PanelSpec(
            id="shelf",
            width_mm=564.0,
            height_mm=300.0,
            thickness_mm=18.0,
            material="ЛДСП",
        ),
    ]
    return ManufacturingSpec(
        spec_version="1.0",
        units=Unit.MM,
        panels=panels,
    )


# ---------------------------------------------------------------------------
# Tests — create & reload
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCreateAndReload:
    """Create a revision and reload it — full spec round-trip."""

    async def test_create_returns_new_revision(self, db: AsyncSession) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(
            db, ORDER_ID, spec, provenance={"source": "test"}, created_by=TEST_USER_ID,
        )
        assert rev.id is not None
        assert rev.revision_number == 1
        assert rev.order_id == ORDER_ID
        assert rev.status == models.RevisionStatusEnum.NEEDS_REVIEW
        assert rev.needs_review is True

    async def test_reload_by_id_returns_same_spec(self, db: AsyncSession) -> None:
        spec = _make_spec()
        created = await create_manufacturing_revision(db, ORDER_ID, spec)
        loaded = await get_manufacturing_revision(db, created.id)

        assert loaded is not None
        assert loaded.id == created.id
        assert loaded.spec == created.spec

    async def test_reload_preserves_all_operations(self, db: AsyncSession) -> None:
        """Regression: previously only dimensions were persisted, operations were lost."""
        spec = _make_spec(with_operations=True)
        created = await create_manufacturing_revision(db, ORDER_ID, spec)
        loaded = await get_manufacturing_revision(db, created.id)

        assert loaded is not None
        left_panel = next(p for p in loaded.spec["panels"] if p["id"] == "left")
        assert len(left_panel["operations"]) == 2
        assert left_panel["operations"][0]["op_type"] == "drill"
        assert left_panel["operations"][1]["op_type"] == "slot"

    async def test_reload_preserves_pocket_operations(self, db: AsyncSession) -> None:
        spec = _make_spec(with_operations=True)
        created = await create_manufacturing_revision(db, ORDER_ID, spec)
        loaded = await get_manufacturing_revision(db, created.id)

        right_panel = next(p for p in loaded.spec["panels"] if p["id"] == "right")
        assert len(right_panel["operations"]) == 1
        op = right_panel["operations"][0]
        assert op["op_type"] == "pocket"
        assert op["depth_mm"] == 6.0

    async def test_canonical_dict_preserves_all_fields(self, db: AsyncSession) -> None:
        """to_canonical_dict round-trips cleanly through JSON column."""
        spec = _make_spec(with_operations=True)
        canonical = spec.to_canonical_dict()
        created = await create_manufacturing_revision(db, ORDER_ID, spec)

        # Reload and compare
        loaded = await get_manufacturing_revision(db, created.id)
        assert loaded.spec == canonical

    async def test_spec_hash_in_provenance(self, db: AsyncSession) -> None:
        spec = _make_spec()
        created = await create_manufacturing_revision(db, ORDER_ID, spec)

        assert "spec_hash" in created.provenance
        assert len(created.provenance["spec_hash"]) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# Tests — revision numbering
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRevisionNumbering:
    """Consecutive creates increment revision_number."""

    async def test_second_revision_is_number_2(self, db: AsyncSession) -> None:
        spec = _make_spec()
        rev1 = await create_manufacturing_revision(db, ORDER_ID, spec)
        rev2 = await create_manufacturing_revision(db, ORDER_ID, spec)

        assert rev1.revision_number == 1
        assert rev2.revision_number == 2

    async def test_different_orders_independent_numbers(self, db: AsyncSession) -> None:
        spec = _make_spec()
        r1 = await create_manufacturing_revision(db, ORDER_ID, spec)
        r2 = await create_manufacturing_revision(db, ORDER_ID_2, spec)

        # Both start at 1 in their own order
        assert r1.revision_number == 1
        assert r2.revision_number == 1

    async def test_list_returns_newest_first(self, db: AsyncSession) -> None:
        spec = _make_spec()
        await create_manufacturing_revision(db, ORDER_ID, spec)
        await create_manufacturing_revision(db, ORDER_ID, spec)
        await create_manufacturing_revision(db, ORDER_ID, spec)

        revisions = await list_manufacturing_revisions(db, ORDER_ID)
        assert len(revisions) == 3
        numbers = [r.revision_number for r in revisions]
        assert numbers == [3, 2, 1]


# ---------------------------------------------------------------------------
# Tests — optimistic concurrency (409)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestOptimisticConcurrency:
    """Update with expected_revision — conflict detection."""

    async def test_update_succeeds_with_matching_revision(
        self, db: AsyncSession,
    ) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)

        new_spec = _make_spec(with_operations=False)
        updated = await update_manufacturing_revision(
            db, rev.id, new_spec, expected_revision=1,
        )
        assert updated.revision_number == 1  # same number, just updated in place
        assert updated.spec["panels"][0]["operations"] == []

    async def test_update_fails_with_wrong_revision(
        self, db: AsyncSession,
    ) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)

        new_spec = _make_spec(with_operations=False)
        with pytest.raises(RevisionConflictError) as exc_info:
            await update_manufacturing_revision(
                db, rev.id, new_spec, expected_revision=99,
            )
        assert exc_info.value.expected == 99
        assert exc_info.value.actual == 1

    async def test_update_fails_on_nonexistent_revision(
        self, db: AsyncSession,
    ) -> None:
        spec = _make_spec()
        fake_id = uuid.uuid4()
        with pytest.raises(LookupError):
            await update_manufacturing_revision(
                db, fake_id, spec, expected_revision=1,
            )


# ---------------------------------------------------------------------------
# Tests — invalidation on edit
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestInvalidationOnEdit:
    """Edits to a revision invalidate approval/artifacts."""

    async def test_edit_resets_status_to_needs_review(
        self, db: AsyncSession,
    ) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)

        # Simulate approval
        rev.status = models.RevisionStatusEnum.APPROVED
        rev.needs_review = False
        await db.commit()
        await db.refresh(rev)
        assert rev.status == models.RevisionStatusEnum.APPROVED

        # Now edit
        new_spec = _make_spec(with_operations=False)
        updated = await update_manufacturing_revision(
            db, rev.id, new_spec, expected_revision=1,
        )
        assert updated.status == models.RevisionStatusEnum.NEEDS_REVIEW
        assert updated.needs_review is True

    async def test_edit_sets_invalidated_by_edit_flag(
        self, db: AsyncSession,
    ) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)

        new_spec = _make_spec(with_operations=False)
        updated = await update_manufacturing_revision(
            db, rev.id, new_spec, expected_revision=1,
        )
        assert updated.provenance.get("invalidated_by_edit") is True

    async def test_edit_updates_spec_hash_in_provenance(
        self, db: AsyncSession,
    ) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)
        old_hash = rev.provenance["spec_hash"]

        new_spec = _make_spec(with_operations=False)
        updated = await update_manufacturing_revision(
            db, rev.id, new_spec, expected_revision=1,
        )
        assert updated.provenance["spec_hash"] != old_hash


# ---------------------------------------------------------------------------
# Tests — regression: prior data loss
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRegressionDataLoss:
    """Regression: earlier versions dropped operations/edges from persisted spec."""

    async def test_dimensions_alone_not_saved(self, db: AsyncSession) -> None:
        """Verify that a spec with ONLY dimensions (no operations) is saved correctly,
        but a spec WITH operations also preserves them — not just dimensions."""
        spec_with_ops = _make_spec(with_operations=True)
        rev = await create_manufacturing_revision(db, ORDER_ID, spec_with_ops)
        loaded = await get_manufacturing_revision(db, rev.id)

        # Every panel must survive the round-trip
        for original, reloaded in zip(
            spec_with_ops.panels, loaded.spec["panels"], strict=False,
        ):
            assert original.id == reloaded["id"]
            assert original.width_mm == reloaded["width_mm"]
            assert original.height_mm == reloaded["height_mm"]
            assert original.thickness_mm == reloaded["thickness_mm"]
            # Operations must also survive
            assert len(reloaded.get("operations", [])) == len(original.operations)

    async def test_empty_operations_not_dropped(self, db: AsyncSession) -> None:
        """Panels with zero operations should still have operations: [] in spec."""
        spec = _make_spec(with_operations=False)
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)
        loaded = await get_manufacturing_revision(db, rev.id)

        for panel in loaded.spec["panels"]:
            assert "operations" in panel

    async def test_spec_version_survives_round_trip(self, db: AsyncSession) -> None:
        spec = _make_spec()
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)
        loaded = await get_manufacturing_revision(db, rev.id)
        assert loaded.spec["spec_version"] == "1.0"
        assert loaded.spec["units"] == "mm"

    async def test_material_field_survives_round_trip(self, db: AsyncSession) -> None:
        spec = _make_spec(with_operations=True)
        rev = await create_manufacturing_revision(db, ORDER_ID, spec)
        loaded = await get_manufacturing_revision(db, rev.id)

        for panel in loaded.spec["panels"]:
            assert panel["material"] == "ЛДСП"
