from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore
from sqlalchemy.dialects import postgresql  # type: ignore


revision = "0003_vector_fields_hardware"
down_revision = "0002_add_artifact_id_to_cam_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # расширение pgvector (vector)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # добавляем новые колонки в hardware_items
    op.add_column("hardware_items", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("hardware_items", sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True))
    op.add_column("hardware_items", sa.Column("embedding_version", sa.String(length=40), nullable=True))
    op.add_column("hardware_items", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.add_column("hardware_items", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("hardware_items", sa.Column("category", sa.String(length=60), nullable=True))
    op.add_column("hardware_items", sa.Column("material_type", sa.String(length=40), nullable=True))
    op.add_column("hardware_items", sa.Column("thickness_min_mm", sa.Float(), nullable=True))
    op.add_column("hardware_items", sa.Column("thickness_max_mm", sa.Float(), nullable=True))
    op.add_column("hardware_items", sa.Column("price_rub", sa.Float(), nullable=True))
    op.add_column("hardware_items", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # создаем векторную колонку истинного типа, если доступен pgvector
    # примечание: при использовании SQLAlchemy Vector тип создается на уровне моделей; здесь альтернативно
    # можно выполнить ALTER TABLE для приведения массива к vector, но для простоты оставим массив,
    # а индексы и тип vector добавим последующей миграцией при наличии pgvector/sqlalchemy Vector.


def downgrade() -> None:
    op.drop_column("hardware_items", "is_active")
    op.drop_column("hardware_items", "price_rub")
    op.drop_column("hardware_items", "thickness_max_mm")
    op.drop_column("hardware_items", "thickness_min_mm")
    op.drop_column("hardware_items", "material_type")
    op.drop_column("hardware_items", "category")
    op.drop_column("hardware_items", "indexed_at")
    op.drop_column("hardware_items", "content_hash")
    op.drop_column("hardware_items", "embedding_version")
    op.drop_column("hardware_items", "embedding")
    op.drop_column("hardware_items", "description")
