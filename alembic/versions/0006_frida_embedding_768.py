"""Миграция на FRIDA embeddings (1536 dim)

Изменяет размерность вектора с 256 на 1536 для использования
модели FRIDA (ai-forever/FRIDA) вместо Yandex Embeddings.

Revision ID: 0006_frida_embedding_768
Revises: 396bcc1972dc
Create Date: 2026-01-16

"""

from alembic import op

revision = "0006_frida_embedding_768"
down_revision = "396bcc1972dc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Удаляем старый индекс (он привязан к размерности 256)
    op.execute("DROP INDEX IF EXISTS idx_hardware_items_embedding")

    # 2. Очищаем старые embeddings (несовместимы по размерности)
    op.execute("""
        UPDATE hardware_items
        SET embedding = NULL,
            embedding_version = NULL,
            content_hash = NULL,
            indexed_at = NULL
    """)

    # 3. Изменяем размерность колонки vector(256) → vector(1536)
    op.execute("""
        ALTER TABLE hardware_items
        ALTER COLUMN embedding TYPE vector(1536)
    """)

    # 4. Создаём новый индекс для 1536-мерных векторов
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
    # 1. Удаляем новый индекс
    op.execute("DROP INDEX IF EXISTS idx_hardware_items_embedding")

    # 2. Очищаем embeddings (1536 не влезут в 256)
    op.execute("""
        UPDATE hardware_items
        SET embedding = NULL,
            embedding_version = NULL,
            content_hash = NULL,
            indexed_at = NULL
    """)

    # 3. Возвращаем размерность 256
    op.execute("""
        ALTER TABLE hardware_items
        ALTER COLUMN embedding TYPE vector(256)
    """)

    # 4. Пересоздаём индекс для 256-мерных векторов
    with op.get_context().autocommit_block():
        op.execute("""
            CREATE INDEX CONCURRENTLY idx_hardware_items_embedding
            ON hardware_items
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)
