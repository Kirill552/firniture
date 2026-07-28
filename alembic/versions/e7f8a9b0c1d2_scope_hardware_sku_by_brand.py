"""Scope hardware SKU uniqueness to each brand.

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
"""

from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def _drop_sku_unique_constraints() -> None:
    op.execute(
        """
        DO $$
        DECLARE constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT con.conname
                FROM pg_constraint AS con
                JOIN pg_attribute AS att
                  ON att.attrelid = con.conrelid
                 AND att.attnum = ANY(con.conkey)
                WHERE con.conrelid = 'hardware_items'::regclass
                  AND con.contype = 'u'
                  AND att.attname = 'sku'
                  AND array_length(con.conkey, 1) = 1
            LOOP
                EXECUTE format(
                    'ALTER TABLE hardware_items DROP CONSTRAINT %I',
                    constraint_name
                );
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    _drop_sku_unique_constraints()
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = 'hardware_items'::regclass
                  AND conname = 'uq_hardware_items_brand_sku'
            ) THEN
                ALTER TABLE hardware_items
                    ADD CONSTRAINT uq_hardware_items_brand_sku UNIQUE (brand, sku);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE hardware_items
            DROP CONSTRAINT IF EXISTS uq_hardware_items_brand_sku;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint AS con
                JOIN pg_attribute AS brand_att
                  ON brand_att.attrelid = con.conrelid
                 AND brand_att.attnum = ANY(con.conkey)
                WHERE con.conrelid = 'hardware_items'::regclass
                  AND con.contype = 'u'
                  AND brand_att.attname = 'sku'
                  AND array_length(con.conkey, 1) = 1
            ) THEN
                ALTER TABLE hardware_items
                    ADD CONSTRAINT hardware_items_sku_key UNIQUE (sku);
            END IF;
        END $$;
        """
    )
