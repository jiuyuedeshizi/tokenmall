"""allow phone only users"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260401_0006"
down_revision = "20260331_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=True)
    else:
        bind.execute(sa.text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM users WHERE email IS NULL"))
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=False)
    else:
        bind.execute(sa.text("ALTER TABLE users ALTER COLUMN email SET NOT NULL"))
