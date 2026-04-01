"""baseline schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.session import Base

# revision identifiers, used by Alembic.
revision = "20260331_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_column(bind: sa.Connection, inspector: sa.Inspector, table_name: str, column_name: str, ddl: str) -> None:
    if not _has_column(inspector, table_name, column_name):
        bind.execute(sa.text(ddl))


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)

    _ensure_column(
        bind,
        inspector,
        "wallet_accounts",
        "reserved_balance",
        "ALTER TABLE wallet_accounts ADD COLUMN reserved_balance NUMERIC(18,6) NOT NULL DEFAULT 0.000000",
    )
    _ensure_column(
        bind,
        inspector,
        "api_keys",
        "encrypted_key",
        "ALTER TABLE api_keys ADD COLUMN encrypted_key VARCHAR(255) NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "users",
        "phone",
        "ALTER TABLE users ADD COLUMN phone VARCHAR(32)",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "model_id",
        "ALTER TABLE model_catalog ADD COLUMN model_id VARCHAR(160) NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "capability_type",
        "ALTER TABLE model_catalog ADD COLUMN capability_type VARCHAR(32) NOT NULL DEFAULT 'chat'",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "vendor_display_name",
        "ALTER TABLE model_catalog ADD COLUMN vendor_display_name VARCHAR(120) NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "billing_mode",
        "ALTER TABLE model_catalog ADD COLUMN billing_mode VARCHAR(32) NOT NULL DEFAULT 'token'",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "pricing_items",
        "ALTER TABLE model_catalog ADD COLUMN pricing_items TEXT NOT NULL DEFAULT '[]'",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "rating",
        "ALTER TABLE model_catalog ADD COLUMN rating NUMERIC(4,2) NOT NULL DEFAULT 4.80",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "hero_description",
        "ALTER TABLE model_catalog ADD COLUMN hero_description TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "support_features",
        "ALTER TABLE model_catalog ADD COLUMN support_features TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "tags",
        "ALTER TABLE model_catalog ADD COLUMN tags TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "example_python",
        "ALTER TABLE model_catalog ADD COLUMN example_python TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "example_typescript",
        "ALTER TABLE model_catalog ADD COLUMN example_typescript TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "model_catalog",
        "example_curl",
        "ALTER TABLE model_catalog ADD COLUMN example_curl TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "usage_logs",
        "billing_quantity",
        "ALTER TABLE usage_logs ADD COLUMN billing_quantity INTEGER NOT NULL DEFAULT 0",
    )
    _ensure_column(
        bind,
        inspector,
        "usage_logs",
        "billing_unit",
        "ALTER TABLE usage_logs ADD COLUMN billing_unit VARCHAR(32) NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "usage_logs",
        "response_time_ms",
        "ALTER TABLE usage_logs ADD COLUMN response_time_ms INTEGER",
    )
    _ensure_column(
        bind,
        inspector,
        "usage_logs",
        "billing_source",
        "ALTER TABLE usage_logs ADD COLUMN billing_source VARCHAR(32) NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "usage_reservations",
        "billing_source",
        "ALTER TABLE usage_reservations ADD COLUMN billing_source VARCHAR(32) NOT NULL DEFAULT ''",
    )
    _ensure_column(
        bind,
        inspector,
        "payment_orders",
        "channel_order_no",
        "ALTER TABLE payment_orders ADD COLUMN channel_order_no VARCHAR(128)",
    )
    _ensure_column(
        bind,
        inspector,
        "payment_orders",
        "payment_url",
        "ALTER TABLE payment_orders ADD COLUMN payment_url VARCHAR(2000)",
    )
    _ensure_column(
        bind,
        inspector,
        "payment_orders",
        "qr_code",
        "ALTER TABLE payment_orders ADD COLUMN qr_code VARCHAR(2000)",
    )
    _ensure_column(
        bind,
        inspector,
        "payment_orders",
        "qr_code_image",
        "ALTER TABLE payment_orders ADD COLUMN qr_code_image VARCHAR(5000)",
    )

    if _has_column(inspector, "users", "phone"):
        bind.execute(
            sa.text(
                "UPDATE users SET phone = '13800000000' "
                "WHERE email IS NOT NULL AND (phone IS NULL OR phone = '')"
            )
        )

    if _has_column(inspector, "model_catalog", "price_source"):
        bind.execute(sa.text("ALTER TABLE model_catalog DROP COLUMN price_source"))
    if _has_column(inspector, "model_catalog", "last_price_synced_at"):
        bind.execute(sa.text("ALTER TABLE model_catalog DROP COLUMN last_price_synced_at"))
    if _has_column(inspector, "model_catalog", "sync_status"):
        bind.execute(sa.text("ALTER TABLE model_catalog DROP COLUMN sync_status"))
    if _has_column(inspector, "model_catalog", "sync_error"):
        bind.execute(sa.text("ALTER TABLE model_catalog DROP COLUMN sync_error"))

    existing_tables = set(inspector.get_table_names())
    if "bailian_model_cache" in existing_tables:
        bind.execute(sa.text("DROP TABLE bailian_model_cache"))
    if "model_price_snapshots" in existing_tables:
        bind.execute(sa.text("DROP TABLE model_price_snapshots"))

    bind.execute(
        sa.text(
            """
            DELETE FROM wallet_ledger
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY reference_type, reference_id, type
                               ORDER BY id ASC
                           ) AS row_num
                    FROM wallet_ledger
                ) duplicates
                WHERE duplicates.row_num > 1
            )
            """
        )
    )
    bind.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_wallet_ledger_reference "
            "ON wallet_ledger (reference_type, reference_id, type)"
        )
    )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_usage_reservations_status_expires_at "
            "ON usage_reservations (status, expires_at)"
        )
    )
    bind.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_orders_order_no "
            "ON payment_orders (order_no)"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = {
        row["name"] for row in inspector.get_indexes("wallet_ledger")
    } if "wallet_ledger" in inspector.get_table_names() else set()
    if "uq_wallet_ledger_reference" in indexes:
        bind.execute(sa.text("DROP INDEX uq_wallet_ledger_reference"))

    reservation_indexes = {
        row["name"] for row in inspector.get_indexes("usage_reservations")
    } if "usage_reservations" in inspector.get_table_names() else set()
    if "ix_usage_reservations_status_expires_at" in reservation_indexes:
        bind.execute(sa.text("DROP INDEX ix_usage_reservations_status_expires_at"))

    payment_indexes = {
        row["name"] for row in inspector.get_indexes("payment_orders")
    } if "payment_orders" in inspector.get_table_names() else set()
    if "uq_payment_orders_order_no" in payment_indexes:
        bind.execute(sa.text("DROP INDEX uq_payment_orders_order_no"))
