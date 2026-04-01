"""expand amount precision to 6 decimals"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0002"
down_revision = "20260331_0001"
branch_labels = None
depends_on = None


def _alter_numeric_precision(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f"ALTER TABLE {table_name} "
                f"ALTER COLUMN {column_name} TYPE NUMERIC(18,6)"
            )
        )


def upgrade() -> None:
    for table_name, column_name in [
        ("wallet_accounts", "balance"),
        ("wallet_accounts", "reserved_balance"),
        ("wallet_ledger", "amount"),
        ("wallet_ledger", "balance_after"),
        ("usage_reservations", "reserved_amount"),
        ("usage_reservations", "actual_amount"),
        ("usage_logs", "amount"),
        ("api_keys", "budget_limit"),
        ("api_keys", "used_amount"),
    ]:
        _alter_numeric_precision(table_name, column_name)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name, column_name in [
            ("wallet_accounts", "balance"),
            ("wallet_accounts", "reserved_balance"),
            ("wallet_ledger", "amount"),
            ("wallet_ledger", "balance_after"),
            ("usage_reservations", "reserved_amount"),
            ("usage_reservations", "actual_amount"),
            ("usage_logs", "amount"),
            ("api_keys", "budget_limit"),
            ("api_keys", "used_amount"),
        ]:
            bind.execute(
                sa.text(
                    f"ALTER TABLE {table_name} "
                    f"ALTER COLUMN {column_name} TYPE NUMERIC(18,4)"
                )
            )
