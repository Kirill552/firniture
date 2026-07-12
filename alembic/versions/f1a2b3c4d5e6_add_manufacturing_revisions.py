"""add manufacturing revisions

Revision ID: f1a2b3c4d5e6
Revises: e1a2b3c4d5f6
Create Date: 2026-07-12 00:00:00.000000

"""
import sqlalchemy as sa  # type: ignore

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Order-level approval state is the SSOT used by export gates.
    op.add_column(
        "orders",
        sa.Column("manufacturing_revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "orders",
        sa.Column("approved_manufacturing_revision", sa.Integer(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("manufacturing_status", sa.String(20), nullable=False, server_default="draft"),
    )
    op.create_table(
        "manufacturing_revisions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cam_job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cam_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("spec", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Backfill: existing CAM jobs implicitly need human review
    op.execute(
        """
        INSERT INTO manufacturing_revisions (id, cam_job_id, order_id, revision_number, spec, status, needs_review, provenance, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            cj.id,
            cj.order_id,
            1,
            COALESCE(cj.context, '{}'),
            'needs_review',
            true,
            '{"source": "legacy_backfill", "reason": "pre_revision_cam_job"}'::jsonb,
            COALESCE(cj.created_at, now()),
            COALESCE(cj.updated_at, now())
        FROM cam_jobs cj
        WHERE NOT EXISTS (
            SELECT 1 FROM manufacturing_revisions mr WHERE mr.cam_job_id = cj.id
        )
        """
    )


def downgrade() -> None:
    # Безопасно для частично инициализированных test/dev баз: alembic-версия
    # могла сохраниться после прерванного DDL.
    op.drop_table("manufacturing_revisions", if_exists=True)
    op.drop_column("orders", "manufacturing_status", if_exists=True)
    op.drop_column("orders", "approved_manufacturing_revision", if_exists=True)
    op.drop_column("orders", "manufacturing_revision", if_exists=True)
