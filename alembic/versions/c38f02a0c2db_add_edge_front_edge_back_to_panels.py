"""add edge_front edge_back to panels

Revision ID: c38f02a0c2db
Revises: 0e26f2d9df07
Create Date: 2026-01-19 03:34:11.854026

"""
import sqlalchemy as sa  # type: ignore

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = 'c38f02a0c2db'
down_revision = '0e26f2d9df07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем edge_front и edge_back с server_default для существующих записей
    op.add_column('panels', sa.Column('edge_front', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('panels', sa.Column('edge_back', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('panels', 'edge_back')
    op.drop_column('panels', 'edge_front')
