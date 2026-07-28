"""Add historical supplier price records.

Revision ID: d5e6f7a8b9c0
Revises: c2d3e4f5a6b7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d5e6f7a8b9c0"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sku", sa.String(length=120), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("unit", sa.String(length=30), nullable=False, server_default="шт"),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_supplier_prices_sku", "supplier_prices", ["sku"])
    op.create_index("ix_supplier_prices_supplier_id", "supplier_prices", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_supplier_prices_supplier_id", table_name="supplier_prices")
    op.drop_index("ix_supplier_prices_sku", table_name="supplier_prices")
    op.drop_table("supplier_prices")
