"""profile picture: users.avatar_key

Revision ID: 0008_avatar
Revises: 0007_organising
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_avatar"
down_revision: str | None = "0007_organising"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_key", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_key")
