"""telemetry: telemetry_events table, users.is_admin

Revision ID: 0004_telemetry
Revises: 0003_project_music
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_telemetry"
down_revision: str | None = "0003_project_music"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), server_default="ok", nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column(
            "props",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_telemetry_events_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_telemetry_events")),
    )
    op.create_index(
        "ix_telemetry_events_kind_name_created_at",
        "telemetry_events",
        ["kind", "name", "created_at"],
    )
    op.create_index("ix_telemetry_events_created_at", "telemetry_events", ["created_at"])
    op.create_index(
        "ix_telemetry_events_user_id_created_at", "telemetry_events", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_telemetry_events_user_id_created_at", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_created_at", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_kind_name_created_at", table_name="telemetry_events")
    op.drop_table("telemetry_events")
    op.drop_column("users", "is_admin")
