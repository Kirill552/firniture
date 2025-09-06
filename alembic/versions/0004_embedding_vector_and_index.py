from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore
from sqlalchemy.dialects import postgresql  # type: ignore


revision = "0004_embedding_vector_and_index"
down_revision = "0003_vector_fields_hardware"
branch_labels = None
depends_on = None


# Примечание: используем прямые SQL для vector типа и индексов — Alembic/SA не всегда знают о pgvector

def upgrade() -> None:
    # Убедиться, что расширение vector есть
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Если уже есть столбец embedding типа массив — переименуем во временный
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c.get("name") for c in inspector.get_columns("hardware_items")]  # type: ignore

    if "embedding" in cols:
        # Переименуем старый embedding -> embedding_array, чтобы освободить имя
        op.alter_column("hardware_items", "embedding", new_column_name="embedding_array")

    # Добавим новый столбец vector(256)
    op.execute("ALTER TABLE hardware_items ADD COLUMN embedding vector(256)")

    # Попробуем бэкофилл: если есть embedding_array и длина=256
    # Преобразуем float[] -> vector через конструктор vector(array)
    if "embedding_array" in [c.get("name") for c in inspector.get_columns("hardware_items")]:  # type: ignore
        # Где длина массива = 256
        op.execute(
            """
            UPDATE hardware_items
            SET embedding = CASE
                WHEN embedding_array IS NOT NULL AND cardinality(embedding_array) = 256
                THEN embedding_array::vector(256)
                ELSE NULL
            END
            """
        )

    # Индекс для ANN: IVFFLAT по cosine; требуется список (опция) для валидации, поэтому создадим животворяще
    # Настройка списка: в pgvector IVFFLAT требует lists параметр; выберем умеренное значение 100
    # Создадим индекс, если его еще нет
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hardware_items_embedding_ivfflat ON hardware_items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # Можно также создать HNSW (если версия поддерживает). Оставим только IVFFLAT для стабильности.

    # Удалим старый embedding_array, если есть
    if "embedding_array" in [c.get("name") for c in inspector.get_columns("hardware_items")]:  # type: ignore
        op.drop_column("hardware_items", "embedding_array")


def downgrade() -> None:
    # В откате вернем массив, удалим vector и индекс
    # Добавим обратно embedding_array
    op.add_column("hardware_items", sa.Column("embedding_array", postgresql.ARRAY(sa.Float()), nullable=True))

    # Заполним embedding_array из vector (вектор -> массив)
    op.execute(
        """
        UPDATE hardware_items
        SET embedding_array = CASE
            WHEN embedding IS NOT NULL THEN ARRAY(SELECT * FROM unnest(embedding))
            ELSE NULL
        END
        """
    )

    # Удалим индекс и столбец vector
    op.execute("DROP INDEX IF EXISTS ix_hardware_items_embedding_ivfflat")
    op.execute("ALTER TABLE hardware_items DROP COLUMN IF EXISTS embedding")

    # Переименуем embedding_array обратно в embedding
    op.alter_column("hardware_items", "embedding_array", new_column_name="embedding")
