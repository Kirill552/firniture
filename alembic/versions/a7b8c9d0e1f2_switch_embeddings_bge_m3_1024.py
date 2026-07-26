"""switch embeddings to bge-m3 1024 dim

Переход с OpenAI text-embedding-3-small (1536) на Cloud.ru bge-m3 (1024).
Старые векторы обнуляются: они несовместимы по пространству, а backfill
(api/scripts/backfill_embeddings.py) пересоздаст их новой моделью.

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-07-26
"""

from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Старые openai-векторы бесполезны в новом пространстве — обнуляем до backfill
    op.execute("UPDATE hardware_items SET embedding = NULL, embedding_version = NULL")
    op.execute("ALTER TABLE hardware_items ALTER COLUMN embedding TYPE vector(1024)")


def downgrade() -> None:
    op.execute("UPDATE hardware_items SET embedding = NULL, embedding_version = NULL")
    op.execute("ALTER TABLE hardware_items ALTER COLUMN embedding TYPE vector(1536)")
