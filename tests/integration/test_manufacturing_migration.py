"""Integration tests for manufacturing_revisions migration.

Focused on upgrade/downgrade correctness and legacy needs_review backfill.
No routes — pure DB-level validation.
"""
from __future__ import annotations

import uuid

import pytest
from alembic.command import downgrade, stamp, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def alembic_cfg() -> Config:
    """Alembic config pointing at the repo's alembic.ini."""
    return Config("alembic.ini")


@pytest.fixture()
def sync_engine():
    """Synchronous engine for migration tests (uses the same DB as async)."""
    from api.settings import settings
    url = (
        f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    engine = create_engine(url, echo=False)
    yield engine
    engine.dispose()


# The migration under test depends on tables created by earlier migrations
# (factories, orders, cam_jobs).  On a fresh DB these don't exist yet, so we
# apply all prerequisite migrations and clean up leftover test data before each
# test method.  After the fixture the DB is at revision e1a2b3c4d5f6 with
# empty prerequisite tables — exactly the state the backfill tests expect.
PREREQUISITE_REVISION = "e1a2b3c4d5f6"
TARGET_REVISION = "f1a2b3c4d5e6"


def _get_current_alembic_revision(sync_engine):
    """Return current alembic version from the DB, or None if fresh."""
    try:
        with sync_engine.connect() as conn:
            return conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    except Exception:
        return None


def _upgrade(sync_engine, alembic_cfg, revision):
    """Run alembic upgrade using *sync_engine* as the connectable.

    Injects ``sync_engine`` into ``alembic_cfg.attributes["connectable"]``
    so ``env.py``'s ``run_migrations_online`` reuses it instead of creating
    a separate engine.  This eliminates cross-engine transaction visibility
    gaps between alembic DDL and test queries.
    """
    alembic_cfg.attributes["connectable"] = sync_engine
    try:
        upgrade(alembic_cfg, revision)
    finally:
        alembic_cfg.attributes.pop("connectable", None)


def _downgrade(sync_engine, alembic_cfg, revision):
    """Run alembic downgrade using *sync_engine* as the connectable."""
    alembic_cfg.attributes["connectable"] = sync_engine
    try:
        downgrade(alembic_cfg, revision)
    finally:
        alembic_cfg.attributes.pop("connectable", None)


def _stamp(sync_engine, alembic_cfg, revision):
    """Set Alembic's marker when a previous interrupted run left only metadata."""
    alembic_cfg.attributes["connectable"] = sync_engine
    try:
        stamp(alembic_cfg, revision)
    finally:
        alembic_cfg.attributes.pop("connectable", None)


def _prerequisite_tables_exist(sync_engine) -> bool:
    """Проверить фактическую схему, а не только значение alembic_version."""
    with sync_engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('factories', 'orders', 'cam_jobs')
                """
            )
        ).fetchall()
    return {row[0] for row in rows} == {"factories", "orders", "cam_jobs"}


@pytest.fixture(autouse=True)
def prerequisite_migrations(alembic_cfg, sync_engine):
    """Bring the DB to PREREQUISITE_REVISION with clean test data.

    Uses ``sync_engine`` as the alembic connectable so migrations and test
    queries share the same connection pool — no cross-engine visibility gaps.
    ``alembic.command.upgrade`` only migrates *forward*; we detect the
    current revision and call ``downgrade`` when the DB is ahead.
    """
    current = _get_current_alembic_revision(sync_engine)
    if current in {PREREQUISITE_REVISION, TARGET_REVISION} and not _prerequisite_tables_exist(sync_engine):
        # Восстановление после прерванного прогона, который успел записать
        # revision stamp, но не создал prerequisite-схему.
        _stamp(sync_engine, alembic_cfg, "base")
        _upgrade(sync_engine, alembic_cfg, PREREQUISITE_REVISION)
    elif current is None:
        _upgrade(sync_engine, alembic_cfg, PREREQUISITE_REVISION)
    elif current == PREREQUISITE_REVISION:
        pass  # already at the right revision
    elif current == TARGET_REVISION:
        _downgrade(sync_engine, alembic_cfg, PREREQUISITE_REVISION)
    else:
        _downgrade(sync_engine, alembic_cfg, "base")
        _upgrade(sync_engine, alembic_cfg, PREREQUISITE_REVISION)
    # Truncate tables that backfill tests seed into, so each test starts clean.
    # Keep factories/users: shared API fixtures use the same test identity, and
    # truncating factories with CASCADE would remove that FK prerequisite.
    # CASCADE handles FK-dependent children (product_configs, dialogue_messages, etc.).
    # manufacturing_revisions doesn't exist at this revision, so no need to clean it.
    with sync_engine.begin() as conn:
        conn.execute(text("TRUNCATE orders, cam_jobs CASCADE"))
    yield


def _table_exists(engine, table_name: str) -> bool:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :t)"),
            {"t": table_name},
        ).scalar_one()


def _column_names(engine, table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
            {"t": table_name},
        ).fetchall()
        return {r[0] for r in rows}


FACTORY_ID = "00000000-0000-0000-0000-000000000001"


def _seed_factory(conn) -> None:
    """Insert a minimal factories row so order FKs resolve."""
    conn.execute(
        text(
            "INSERT INTO factories (id, name, created_at)"
            " VALUES (:fid, 'Test Factory', now())"
            " ON CONFLICT (id) DO NOTHING"
        ),
        {"fid": FACTORY_ID},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestManufacturingRevisionsMigration:
    """Upgrade / downgrade cycle for the manufacturing_revisions table."""

    def test_upgrade_creates_table(self, alembic_cfg, sync_engine):
        """Upgrade to f1a2b3c4d5e6 creates manufacturing_revisions."""
        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)
        assert _table_exists(sync_engine, "manufacturing_revisions"), (
            "manufacturing_revisions should exist after upgrade"
        )

    def test_upgrade_creates_expected_columns(self, alembic_cfg, sync_engine):
        """All expected columns are present."""
        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)
        cols = _column_names(sync_engine, "manufacturing_revisions")
        expected = {
            "id",
            "cam_job_id",
            "order_id",
            "revision_number",
            "spec",
            "status",
            "needs_review",
            "provenance",
            "created_by",
            "created_at",
            "updated_at",
        }
        missing = expected - cols
        assert not missing, f"Missing columns: {missing}"

    def test_downgrade_drops_table(self, alembic_cfg, sync_engine):
        """Downgrade from f1a2b3c4d5e6 removes the table."""
        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)
        assert _table_exists(sync_engine, "manufacturing_revisions")

        _downgrade(sync_engine, alembic_cfg, PREREQUISITE_REVISION)
        assert not _table_exists(sync_engine, "manufacturing_revisions"), (
            "manufacturing_revisions should not exist after downgrade"
        )

    def test_backfill_creates_revision_per_cam_job(self, alembic_cfg, sync_engine):
        """Each existing cam_job gets exactly one legacy revision row."""
        job_id = uuid.uuid4()
        order_id = uuid.uuid4()

        with sync_engine.begin() as conn:
            _seed_factory(conn)
            conn.execute(
                text("INSERT INTO orders (id, factory_id, status, created_at, updated_at) VALUES (:oid, :fid, 'draft', now(), now())"),
                {"oid": str(order_id), "fid": FACTORY_ID},
            )
            conn.execute(
                text(
                    "INSERT INTO cam_jobs (id, order_id, job_kind, status, created_at, updated_at, attempt)"
                    " VALUES (:jid, :oid, 'DXF', 'Created', now(), now(), 0)"
                ),
                {"jid": str(job_id), "oid": str(order_id)},
            )

        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)

        with sync_engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM manufacturing_revisions WHERE cam_job_id = :jid"),
                {"jid": str(job_id)},
            ).scalar_one()
        assert count == 1, f"Expected 1 revision per cam_job, got {count}"

    def test_backfill_sets_needs_review_true(self, alembic_cfg, sync_engine):
        """Legacy backfill rows have needs_review = true."""
        job_id = uuid.uuid4()
        order_id = uuid.uuid4()

        with sync_engine.begin() as conn:
            _seed_factory(conn)
            conn.execute(
                text("INSERT INTO orders (id, factory_id, status, created_at, updated_at) VALUES (:oid, :fid, 'draft', now(), now())"),
                {"oid": str(order_id), "fid": FACTORY_ID},
            )
            conn.execute(
                text(
                    "INSERT INTO cam_jobs (id, order_id, job_kind, status, created_at, updated_at, attempt)"
                    " VALUES (:jid, :oid, 'GCODE', 'Completed', now(), now(), 0)"
                ),
                {"jid": str(job_id), "oid": str(order_id)},
            )

        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)

        with sync_engine.connect() as conn:
            row = conn.execute(
                text("SELECT needs_review, status, provenance FROM manufacturing_revisions WHERE cam_job_id = :jid"),
                {"jid": str(job_id)},
            ).fetchone()
        assert row is not None, "Revision row should exist"
        assert row[0] is True, "needs_review should be True for legacy backfill"
        assert row[1] == "needs_review", "status should be 'needs_review' for legacy"

    def test_backfill_provenance_tagged(self, alembic_cfg, sync_engine):
        """Legacy backfill provenance contains the legacy_backfill source tag."""
        job_id = uuid.uuid4()
        order_id = uuid.uuid4()

        with sync_engine.begin() as conn:
            _seed_factory(conn)
            conn.execute(
                text("INSERT INTO orders (id, factory_id, status, created_at, updated_at) VALUES (:oid, :fid, 'draft', now(), now())"),
                {"oid": str(order_id), "fid": FACTORY_ID},
            )
            conn.execute(
                text(
                    "INSERT INTO cam_jobs (id, order_id, job_kind, status, created_at, updated_at, attempt)"
                    " VALUES (:jid, :oid, 'DXF', 'Failed', now(), now(), 0)"
                ),
                {"jid": str(job_id), "oid": str(order_id)},
            )
        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)

        with sync_engine.connect() as conn:
            prov = conn.execute(
                text("SELECT provenance FROM manufacturing_revisions WHERE cam_job_id = :jid"),
                {"jid": str(job_id)},
            ).scalar_one()
        assert prov["source"] == "legacy_backfill", "Provenance source should be 'legacy_backfill'"

    def test_no_cam_jobs_backfill_empty(self, alembic_cfg, sync_engine):
        """With no cam_jobs, upgrade still succeeds and table is empty."""
        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)

        with sync_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM manufacturing_revisions")).scalar_one()
        assert count == 0

    def test_idempotent_backfill(self, alembic_cfg, sync_engine):
        """Running upgrade twice does not duplicate backfill rows."""
        job_id = uuid.uuid4()
        order_id = uuid.uuid4()

        with sync_engine.begin() as conn:
            _seed_factory(conn)
            conn.execute(
                text("INSERT INTO orders (id, factory_id, status, created_at, updated_at) VALUES (:oid, :fid, 'draft', now(), now())"),
                {"oid": str(order_id), "fid": FACTORY_ID},
            )
            conn.execute(
                text(
                    "INSERT INTO cam_jobs (id, order_id, job_kind, status, created_at, updated_at, attempt)"
                    " VALUES (:jid, :oid, 'DXF', 'Created', now(), now(), 0)"
                ),
                {"jid": str(job_id), "oid": str(order_id)},
            )

        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)
        # Simulate downgrade + re-upgrade (fresh migration run)
        _downgrade(sync_engine, alembic_cfg, PREREQUISITE_REVISION)
        _upgrade(sync_engine, alembic_cfg, TARGET_REVISION)

        with sync_engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM manufacturing_revisions WHERE cam_job_id = :jid"),
                {"jid": str(job_id)},
            ).scalar_one()
        assert count == 1, "Backfill must be idempotent — exactly 1 row per cam_job"
