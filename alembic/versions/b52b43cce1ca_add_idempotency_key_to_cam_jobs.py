"""add_idempotency_key_to_cam_jobs

Revision ID: b52b43cce1ca
Revises: bfd67af6351f
Create Date: 2025-09-06 11:16:30.481345

"""
from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


# revision identifiers, used by Alembic.
revision = 'b52b43cce1ca'
down_revision = 'bfd67af6351f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cam_jobs', sa.Column('idempotency_key', sa.String(length=50), nullable=True, unique=True))

def downgrade() -> None:
    op.drop_column('cam_jobs', 'idempotency_key')
