from __future__ import annotations

from alembic import op  # type: ignore

revision = "0005_cleanup_embedding_array"
down_revision = "0004_embedding_vector_and_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Дозаполнение vector из массива, если ещё пусто
    op.execute(
        """
        UPDATE hardware_items
        SET embedding = CASE
            WHEN embedding IS NULL AND embedding_array IS NOT NULL AND cardinality(embedding_array) = 256
            THEN embedding_array::vector(256)
            ELSE embedding
        END
        """
    )
    # Удаление временного столбца
    op.execute("ALTER TABLE hardware_items DROP COLUMN IF EXISTS embedding_array")


def downgrade() -> None:
    # Данные не восстанавливаем: unnest(vector) в PG не существует, а backfill
    # embeddings всё равно пересоздаёт векторы. Восстанавливаем только колонку.
    op.execute("ALTER TABLE hardware_items ADD COLUMN IF NOT EXISTS embedding_array double precision[]")
