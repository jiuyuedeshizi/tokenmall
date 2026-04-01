"""add billing quantity and unit to usage logs"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0003"
down_revision = "20260331_0002"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "usage_logs", "billing_quantity"):
        bind.execute(sa.text("ALTER TABLE usage_logs ADD COLUMN billing_quantity INTEGER NOT NULL DEFAULT 0"))
    if not _has_column(inspector, "usage_logs", "billing_unit"):
        bind.execute(sa.text("ALTER TABLE usage_logs ADD COLUMN billing_unit VARCHAR(32) NOT NULL DEFAULT ''"))

    bind.execute(
        sa.text(
            """
            UPDATE usage_logs
            SET billing_unit = CASE
                WHEN COALESCE((
                    SELECT billing_mode
                    FROM model_catalog
                    WHERE model_catalog.model_code = usage_logs.model_code
                    LIMIT 1
                ), 'token') = 'per_image' THEN 'image'
                WHEN COALESCE((
                    SELECT billing_mode
                    FROM model_catalog
                    WHERE model_catalog.model_code = usage_logs.model_code
                    LIMIT 1
                ), 'token') = 'per_second' THEN 'second'
                WHEN COALESCE((
                    SELECT billing_mode
                    FROM model_catalog
                    WHERE model_catalog.model_code = usage_logs.model_code
                    LIMIT 1
                ), 'token') = 'per_10k_chars' THEN 'char'
                ELSE 'token'
            END
            WHERE billing_unit = ''
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE usage_logs
            SET billing_quantity = CASE
                WHEN billing_quantity > 0 THEN billing_quantity
                WHEN total_tokens > 0 THEN total_tokens
                WHEN billing_unit = 'image' AND amount > 0 THEN 1
                ELSE 0
            END
            WHERE billing_quantity = 0
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("ALTER TABLE usage_logs DROP COLUMN IF EXISTS billing_quantity"))
        bind.execute(sa.text("ALTER TABLE usage_logs DROP COLUMN IF EXISTS billing_unit"))
