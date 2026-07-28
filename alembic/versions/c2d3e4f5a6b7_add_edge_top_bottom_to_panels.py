"""Кромка верха и низа детали

Съёмную полку кромят по кругу, а не только по переднему торцу. Без этих
полей метры кромки в смете занижались.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-28

"""
import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "panels",
        sa.Column("edge_top", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "panels",
        sa.Column("edge_bottom", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("panels", "edge_bottom")
    op.drop_column("panels", "edge_top")
