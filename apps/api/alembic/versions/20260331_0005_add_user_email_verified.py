"""add user email verified"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0005"
down_revision = "20260331_0004"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "users", "email_verified"):
        bind.execute(sa.text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE"))
    if not _has_column(inspector, "users", "email_verified_at"):
        bind.execute(sa.text("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP NULL"))

    bind.execute(
        sa.text(
            """
            UPDATE users
            SET email_verified = TRUE,
                email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP)
            WHERE email IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS email_verified_at"))
        bind.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS email_verified"))
