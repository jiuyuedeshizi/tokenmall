from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def _build_alembic_config(database_url: str) -> Config:
    root_dir = Path(__file__).resolve().parents[1]
    config = Config(str(root_dir / "alembic.ini"))
    config.set_main_option("script_location", str(root_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_head_on_empty_database(tmp_path: Path):
    db_path = tmp_path / "empty.sqlite"
    database_url = f"sqlite:///{db_path}"

    command.upgrade(_build_alembic_config(database_url), "head")

    inspector = inspect(create_engine(database_url, future=True))
    tables = set(inspector.get_table_names())
    assert "users" in tables
    assert "wallet_ledger" in tables
    assert "usage_reservations" in tables
    assert "payment_orders" in tables
    assert "verification_codes" in tables
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert "email_verified" in user_columns
    assert "email_verified_at" in user_columns
    email_column = next(column for column in inspector.get_columns("users") if column["name"] == "email")
    assert email_column["nullable"] is True


def test_alembic_upgrade_head_deduplicates_wallet_ledger(tmp_path: Path):
    db_path = tmp_path / "legacy.sqlite"
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255), password_hash VARCHAR(255), name VARCHAR(120), role VARCHAR(32), status VARCHAR(32))"))
        connection.execute(text("CREATE TABLE wallet_accounts (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, balance NUMERIC(18,4) NOT NULL DEFAULT 0.0000, currency VARCHAR(16) NOT NULL DEFAULT 'CNY')"))
        connection.execute(text("CREATE TABLE wallet_ledger (id INTEGER PRIMARY KEY, user_id INTEGER, type VARCHAR(32), amount NUMERIC(18,4), balance_after NUMERIC(18,4), reference_type VARCHAR(32), reference_id VARCHAR(128), description VARCHAR(255))"))
        connection.execute(text("CREATE TABLE usage_reservations (id INTEGER PRIMARY KEY, user_id INTEGER, api_key_id INTEGER, request_id VARCHAR(128), model_code VARCHAR(120), reserved_amount NUMERIC(18,4), actual_amount NUMERIC(18,4), estimated_input_tokens INTEGER, estimated_output_tokens INTEGER, status VARCHAR(32), error_message VARCHAR(255), expires_at DATETIME, created_at DATETIME)"))
        connection.execute(text("CREATE TABLE payment_orders (id INTEGER PRIMARY KEY, order_no VARCHAR(64), user_id INTEGER, amount NUMERIC(18,2), payment_method VARCHAR(32), status VARCHAR(32), created_at DATETIME, updated_at DATETIME)"))
        connection.execute(
            text(
                "INSERT INTO wallet_ledger (id, user_id, type, amount, balance_after, reference_type, reference_id, description) "
                "VALUES "
                "(1, 1, 'recharge', 10, 10, 'payment_order', 'ord_dup', 'first'), "
                "(2, 1, 'recharge', 10, 20, 'payment_order', 'ord_dup', 'second')"
            )
        )

    command.upgrade(_build_alembic_config(database_url), "head")

    with engine.connect() as connection:
        row_count = connection.execute(text("SELECT COUNT(*) FROM wallet_ledger WHERE reference_type = 'payment_order' AND reference_id = 'ord_dup'")).scalar_one()
    inspector = inspect(engine)
    wallet_indexes = {row["name"] for row in inspector.get_indexes("wallet_ledger")}
    reservation_indexes = {row["name"] for row in inspector.get_indexes("usage_reservations")}

    assert row_count == 1
    assert "uq_wallet_ledger_reference" in wallet_indexes
    assert "ix_usage_reservations_status_expires_at" in reservation_indexes
