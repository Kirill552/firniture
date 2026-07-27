"""add payments and order_export_access

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-07-27 00:00:00.000000

Единица тарификации — один заказ целиком. Таблицы:
  payments            — платежи ЮKassa (одиночный заказ или пакет из 10);
  order_export_access — выданный доступ к production-экспорту (одна запись на заказ).

Миграция идемпотентна: повторный upgrade на частично применённой схеме не падает.
"""
import sqlalchemy as sa  # type: ignore
from sqlalchemy.dialects import postgresql  # type: ignore

from alembic import op  # type: ignore

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("factory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("amount_rub", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("yookassa_payment_id", sa.String(64), nullable=True),
        sa.Column("idempotence_key", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["factory_id"], ["factories.id"], name="fk_payments_factory", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_payments_user", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_payments_order", ondelete="SET NULL"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "uq_payments_yookassa_payment_id",
        "payments",
        ["yookassa_payment_id"],
        unique=True,
        if_not_exists=True,
    )
    op.create_index(
        "uq_payments_idempotence_key",
        "payments",
        ["idempotence_key"],
        unique=True,
        if_not_exists=True,
    )
    op.create_index(
        "ix_payments_factory_kind_status",
        "payments",
        ["factory_id", "kind", "status"],
        if_not_exists=True,
    )

    op.create_table(
        "order_export_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("factory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_export_access_order", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["factory_id"], ["factories.id"], name="fk_export_access_factory", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"], name="fk_export_access_payment", ondelete="SET NULL"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "uq_order_export_access_order_id",
        "order_export_access",
        ["order_id"],
        unique=True,
        if_not_exists=True,
    )
    op.create_index(
        "ix_order_export_access_factory_reason",
        "order_export_access",
        ["factory_id", "reason"],
        if_not_exists=True,
    )


def downgrade() -> None:
    # Порядок важен: order_export_access ссылается на payments.
    op.drop_index(
        "ix_order_export_access_factory_reason", table_name="order_export_access", if_exists=True
    )
    op.drop_index(
        "uq_order_export_access_order_id", table_name="order_export_access", if_exists=True
    )
    op.drop_table("order_export_access", if_exists=True)
    op.drop_index("ix_payments_factory_kind_status", table_name="payments", if_exists=True)
    op.drop_index("uq_payments_idempotence_key", table_name="payments", if_exists=True)
    op.drop_index("uq_payments_yookassa_payment_id", table_name="payments", if_exists=True)
    op.drop_table("payments", if_exists=True)
