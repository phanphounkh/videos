"""account plans and monthly limits; last login

Revision ID: 0006_account_plans
Revises: 0005_drop_telemetry_events
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_account_plans"
down_revision: str | None = "0005_drop_telemetry_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("plan", sa.String(32), server_default="free", nullable=False))
    op.add_column("users", sa.Column("limit_ai_calls", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("limit_tokens", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("limit_exports", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in ("last_login_at", "limit_exports", "limit_tokens", "limit_ai_calls", "plan"):
        op.drop_column("users", column)
