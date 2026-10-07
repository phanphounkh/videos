"""Project: one video and everything that belongs to it."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AspectRatio, ProjectStatus, VideoStyle

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.render_job import RenderJob
    from app.models.scene import Scene
    from app.models.user import User


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The original user prompt, kept so a project can be regenerated later.
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), default=ProjectStatus.DRAFT, nullable=False, index=True
    )
    # Language lives on BOTH project and scene: the project default drives script
    # generation; per-scene overrides allow a bilingual video later.
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(
        String(16), default=AspectRatio.LANDSCAPE, nullable=False
    )
    style: Mapped[str] = mapped_column(String(32), default=VideoStyle.EDUCATIONAL, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voice: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Target duration requested by the user, in seconds.
    target_duration: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    thumbnail_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="projects")
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Scene.scene_number",
        lazy="selectin",
    )
    render_jobs: Mapped[list["RenderJob"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(RenderJob.created_at)",
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="Asset.project_id",
    )

    @property
    def dimensions(self) -> tuple[int, int]:
        return AspectRatio(self.aspect_ratio).dimensions

    @property
    def duration(self) -> float:
        """Actual duration = sum of scene durations (not the requested target)."""
        return round(sum(scene.duration for scene in self.scenes), 2)

    def __repr__(self) -> str:
        return f"<Project {self.title!r} status={self.status}>"
