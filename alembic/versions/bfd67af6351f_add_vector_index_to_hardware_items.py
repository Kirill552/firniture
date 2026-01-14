"""add_vector_index_to_hardware_items

Revision ID: bfd67af6351f
Revises: 0005_cleanup_embedding_array
Create Date: 2025-09-06 11:04:55.475691

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'bfd67af6351f'
down_revision = '0005_cleanup_embedding_array'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET statement_timeout = '300s'")
    op.execute("SET lock_timeout = '10s'")
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE INDEX CONCURRENTLY idx_hardware_items_embedding
            ON hardware_items
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_hardware_items_embedding")
