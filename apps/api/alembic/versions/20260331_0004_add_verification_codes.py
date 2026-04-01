"""add verification codes"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0004"
down_revision = "20260331_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "verification_codes" not in existing_tables:
        op.create_table(
            "verification_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("channel", sa.String(length=32), nullable=False),
            sa.Column("target", sa.String(length=255), nullable=False),
            sa.Column("purpose", sa.String(length=32), nullable=False, server_default="login"),
            sa.Column("code_hash", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("send_window_started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("send_attempts_in_window", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verify_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("channel", "target", "purpose", name="uq_verification_codes_channel_target_purpose"),
        )

    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_verification_codes_channel ON verification_codes (channel)"))
    bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_verification_codes_target ON verification_codes (target)"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("DROP TABLE IF EXISTS verification_codes"))
