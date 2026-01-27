"""add drilling_points to panels

Revision ID: e1a2b3c4d5f6
Revises: c38f02a0c2db
Create Date: 2026-01-22

"""
import sqlalchemy as sa  # type: ignore

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5f6'
down_revision = 'c38f02a0c2db'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем JSON поле для точек присадки (сверления)
    # Формат: [{"x": float, "y": float, "diameter": float, "depth": float, "side": "face"|"edge", "hardware_type": str}]
    op.add_column('panels', sa.Column('drilling_points', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('panels', 'drilling_points')
