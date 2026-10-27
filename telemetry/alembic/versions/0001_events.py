"""events

Revision ID: 0001_events
Revises:
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_events"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("level", sa.String(8), nullable=False, server_default="info"),
        sa.Column("outcome", sa.String(8), nullable=True),
        sa.Column("user_id", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("path", sa.String(300), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(50), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column(
            "properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("platform", sa.String(16), nullable=True),
        sa.Column("os", sa.String(60), nullable=True),
        sa.Column("browser", sa.String(60), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("seq", name="uq_events_seq"),
    )
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_type_name_created", "events", ["event_type", "name", "created_at"])
    op.create_index("ix_events_source_created", "events", ["source", "created_at"])
    op.create_index("ix_events_user_created", "events", ["user_id", "created_at"])
    op.create_index("ix_events_session_created", "events", ["session_id", "created_at"])
    op.create_index("ix_events_request", "events", ["request_id"])
    op.create_index(
        "ix_events_errors", "events", ["created_at"], postgresql_where=sa.text("level = 'error'")
    )


def downgrade() -> None:
    op.drop_table("events")
