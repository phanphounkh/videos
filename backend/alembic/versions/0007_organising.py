"""folders, starred projects, trash, storage limit

Revision ID: 0007_organising
Revises: 0006_account_plans
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_organising"
down_revision: str | None = "0006_account_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_folders_owner_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_folders"),
    )
    op.create_index("ix_folders_owner_id", "folders", ["owner_id"])
    op.add_column(
        "projects", sa.Column("starred", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column("projects", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_projects_folder_id_folders",
        "projects",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_folder_id", "projects", ["folder_id"])
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"])
    op.add_column("users", sa.Column("limit_storage_mb", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "limit_storage_mb")
    op.drop_index("ix_projects_deleted_at", "projects")
    op.drop_index("ix_projects_folder_id", "projects")
    op.drop_constraint("fk_projects_folder_id_folders", "projects", type_="foreignkey")
    for column in ("deleted_at", "folder_id", "starred"):
        op.drop_column("projects", column)
    op.drop_index("ix_folders_owner_id", "folders")
    op.drop_table("folders")
