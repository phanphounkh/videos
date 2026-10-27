"""selectable hosts: custom_avatars, users.avatar_default/avatar_auto, projects.avatar

Revision ID: 0009_avatars
Revises: 0008_avatar
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_avatars"
down_revision: str | None = "0008_avatar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "custom_avatars",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("mode", sa.String(16), server_default="mouth", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_custom_avatars_owner_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_custom_avatars"),
    )
    op.create_index("ix_custom_avatars_owner_id", "custom_avatars", ["owner_id"])
    op.add_column("users", sa.Column("avatar_default", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("avatar_auto", sa.Boolean(), server_default="true", nullable=False)
    )
    op.add_column("projects", sa.Column("avatar", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "avatar")
    op.drop_column("users", "avatar_auto")
    op.drop_column("users", "avatar_default")
    op.drop_index("ix_custom_avatars_owner_id", table_name="custom_avatars")
    op.drop_table("custom_avatars")
