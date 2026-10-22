"""project music: projects.music_asset_id, projects.settings

Revision ID: 0003_project_music
Revises: 0002_video_purpose
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_project_music"
down_revision: str | None = "0002_video_purpose"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("projects", sa.Column("music_asset_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_projects_music_asset_id_assets"),
        "projects",
        "assets",
        ["music_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_projects_music_asset_id_assets"), "projects", type_="foreignkey")
    op.drop_column("projects", "music_asset_id")
    op.drop_column("projects", "settings")
