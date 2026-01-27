"""add_factory_settings

Revision ID: 0e26f2d9df07
Revises: 5e11f580316b
Create Date: 2026-01-16 15:23:26.348701

"""
import sqlalchemy as sa  # type: ignore

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = '0e26f2d9df07'
down_revision = '5e11f580316b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем JSON поле settings в таблицу factories
    op.add_column('factories', sa.Column('settings', sa.JSON(), nullable=False, server_default='{}'))


def downgrade() -> None:
    op.drop_column('factories', 'settings')
