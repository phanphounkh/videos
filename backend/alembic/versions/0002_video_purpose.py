"""video purpose: projects.purpose, projects.presenter, projects.cta_text

Revision ID: 0002_video_purpose
Revises: 0001_initial
Create Date: 2026-10-22

Existing projects are stories told by the host, which is exactly what the server
defaults give them, so no data migration is needed.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_video_purpose"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("purpose", sa.String(32), server_default="story", nullable=False),
    )
    op.add_column(
        "projects",
        sa.Column("presenter", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("projects", sa.Column("cta_text", sa.String(60), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "cta_text")
    op.drop_column("projects", "presenter")
    op.drop_column("projects", "purpose")
