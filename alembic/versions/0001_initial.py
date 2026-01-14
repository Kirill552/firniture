from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("customer_ref", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "product_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("width_mm", sa.Float(), nullable=False),
        sa.Column("height_mm", sa.Float(), nullable=False),
        sa.Column("depth_mm", sa.Float(), nullable=False),
        sa.Column("material", sa.String(length=80), nullable=True),
        sa.Column("thickness_mm", sa.Float(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "panels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_configs.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("width_mm", sa.Float(), nullable=False),
        sa.Column("height_mm", sa.Float(), nullable=False),
        sa.Column("thickness_mm", sa.Float(), nullable=False),
        sa.Column("material", sa.String(length=80), nullable=True),
        sa.Column("edge_band_mm", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=120), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "hardware_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sku", sa.String(length=120), nullable=False, unique=True),
        sa.Column("brand", sa.String(length=80), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("compat", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("url", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=40), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="SET NULL")),
    )

    op.create_table(
        "bom_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE")),
        sa.Column("sku", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("supplier_sku", sa.String(length=120), nullable=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="SET NULL")),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("presigned_url", sa.String(length=512), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "cam_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column("job_kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_role", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("related_entity", sa.String(length=40), nullable=False),
        sa.Column("related_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "validation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("validation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("validations.id", ondelete="CASCADE")),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("current_value", sa.JSON(), nullable=True),
        sa.Column("proposed_value", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    for table in [
        "validation_items",
        "validations",
        "audit_logs",
        "cam_jobs",
        "artifacts",
        "bom_items",
        "hardware_items",
        "suppliers",
        "panels",
        "product_configs",
        "orders",
    ]:
        op.drop_table(table)
