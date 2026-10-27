"""initial schema: users, projects, scenes, assets, captions, voice_generations, render_jobs

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-07

Hand-ordered on purpose. The schema contains a deliberate reference cycle:

    assets.project_id  -> projects.id      (an asset belongs to a project)
    assets.scene_id    -> scenes.id        (and optionally to a scene)
    projects.thumbnail_asset_id -> assets.id   (which image represents the project)
    scenes.image/video/audio_asset_id -> assets.id  (which asset the scene uses)

A cycle cannot be expressed with inline FOREIGN KEY clauses, so the tables are
created first and the back-referencing constraints are added afterwards with
ALTER TABLE. `alembic revision --autogenerate` sorts tables alphabetically and
therefore cannot produce this ordering by itself.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
NOW = sa.text("now()")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", TS, server_default=NOW, nullable=False),
        sa.Column("updated_at", TS, server_default=NOW, nullable=False),
    ]


def upgrade() -> None:
    # ---------------------------------------------------------------- users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ------------------------------------------------------------- projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("style", sa.String(length=32), nullable=False),
        sa.Column("tone", sa.String(length=64), nullable=True),
        sa.Column("audience", sa.String(length=128), nullable=True),
        sa.Column("voice", sa.String(length=64), nullable=True),
        sa.Column("target_duration", sa.Integer(), nullable=False),
        sa.Column("fps", sa.Integer(), nullable=False),
        sa.Column("thumbnail_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"],
            name=op.f("fk_projects_owner_id_users"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"])
    op.create_index(op.f("ix_projects_status"), "projects", ["status"])

    # --------------------------------------------------------------- scenes
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_number", sa.Integer(), nullable=False),
        sa.Column("narration", sa.Text(), nullable=False),
        sa.Column("visual_prompt", sa.Text(), nullable=True),
        sa.Column("on_screen_text", sa.Text(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("transition", sa.String(length=16), nullable=False),
        sa.Column("background_color", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("image_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("video_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("audio_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name=op.f("fk_scenes_project_id_projects"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenes")),
        sa.UniqueConstraint("project_id", "scene_number", name="uq_scene_project_number"),
    )
    op.create_index(op.f("ix_scenes_project_id"), "scenes", ["project_id"])

    # --------------------------------------------------------------- assets
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name=op.f("fk_assets_project_id_projects"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"], ["scenes.id"],
            name=op.f("fk_assets_scene_id_scenes"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_assets_storage_key")),
    )
    op.create_index(op.f("ix_assets_project_id"), "assets", ["project_id"])
    op.create_index(op.f("ix_assets_type"), "assets", ["type"])

    # ------------------------------------------------------------- captions
    op.create_table(
        "captions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["scene_id"], ["scenes.id"],
            name=op.f("fk_captions_scene_id_scenes"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_captions")),
    )
    op.create_index(op.f("ix_captions_scene_id"), "captions", ["scene_id"])

    # ---------------------------------------------------- voice_generations
    op.create_table(
        "voice_generations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("voice", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["assets.id"],
            name=op.f("fk_voice_generations_asset_id_assets"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"], ["scenes.id"],
            name=op.f("fk_voice_generations_scene_id_scenes"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_generations")),
    )
    op.create_index(op.f("ix_voice_generations_scene_id"), "voice_generations", ["scene_id"])

    # ----------------------------------------------------------- render_jobs
    op.create_table(
        "render_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("output_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("logs", sa.Text(), nullable=True),
        sa.Column("started_at", TS, nullable=True),
        sa.Column("completed_at", TS, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["output_asset_id"], ["assets.id"],
            name=op.f("fk_render_jobs_output_asset_id_assets"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"],
            name=op.f("fk_render_jobs_project_id_projects"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_render_jobs")),
    )
    op.create_index(op.f("ix_render_jobs_project_id"), "render_jobs", ["project_id"])
    op.create_index(op.f("ix_render_jobs_status"), "render_jobs", ["status"])

    # --- back-references that close the cycle (added after `assets` exists) --
    op.create_foreign_key(
        op.f("fk_projects_thumbnail_asset_id_assets"),
        "projects", "assets", ["thumbnail_asset_id"], ["id"], ondelete="SET NULL",
    )
    for column in ("image_asset_id", "video_asset_id", "audio_asset_id"):
        op.create_foreign_key(
            op.f(f"fk_scenes_{column}_assets"),
            "scenes", "assets", [column], ["id"], ondelete="SET NULL",
        )


def downgrade() -> None:
    # Drop the cycle-closing constraints first, then the tables in reverse order.
    for column in ("image_asset_id", "video_asset_id", "audio_asset_id"):
        op.drop_constraint(op.f(f"fk_scenes_{column}_assets"), "scenes", type_="foreignkey")
    op.drop_constraint(
        op.f("fk_projects_thumbnail_asset_id_assets"), "projects", type_="foreignkey"
    )

    op.drop_index(op.f("ix_render_jobs_status"), table_name="render_jobs")
    op.drop_index(op.f("ix_render_jobs_project_id"), table_name="render_jobs")
    op.drop_table("render_jobs")

    op.drop_index(op.f("ix_voice_generations_scene_id"), table_name="voice_generations")
    op.drop_table("voice_generations")

    op.drop_index(op.f("ix_captions_scene_id"), table_name="captions")
    op.drop_table("captions")

    op.drop_index(op.f("ix_assets_type"), table_name="assets")
    op.drop_index(op.f("ix_assets_project_id"), table_name="assets")
    op.drop_table("assets")

    op.drop_index(op.f("ix_scenes_project_id"), table_name="scenes")
    op.drop_table("scenes")

    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
