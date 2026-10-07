"""Scene: one shot of the video.

A scene owns its narration, its visual, its voice audio and its captions. Scene
timing is derived (`start_time` is computed from the preceding scenes) rather
than stored twice, so reordering cannot produce an inconsistent timeline.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Transition

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.caption import Caption
    from app.models.project import Project
    from app.models.voice_generation import VoiceGeneration


class Scene(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scenes"
    __table_args__ = (
        # Two scenes in one project can never claim the same position.
        UniqueConstraint("project_id", "scene_number", name="uq_scene_project_number"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    narration: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    on_screen_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    transition: Mapped[str] = mapped_column(String(16), default=Transition.FADE, nullable=False)
    background_color: Mapped[str] = mapped_column(String(16), default="#0b0d12", nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Free-form presentation settings (text position, font size, animation).
    # JSONB because these evolve constantly and do not need to be queryable.
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    image_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    video_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    audio_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="scenes")
    image_asset: Mapped["Asset | None"] = relationship(
        foreign_keys=[image_asset_id], lazy="selectin"
    )
    video_asset: Mapped["Asset | None"] = relationship(
        foreign_keys=[video_asset_id], lazy="selectin"
    )
    audio_asset: Mapped["Asset | None"] = relationship(
        foreign_keys=[audio_asset_id], lazy="selectin"
    )
    captions: Mapped[list["Caption"]] = relationship(
        back_populates="scene",
        cascade="all, delete-orphan",
        order_by="Caption.start_time",
        lazy="selectin",
    )
    voice_generations: Mapped[list["VoiceGeneration"]] = relationship(
        back_populates="scene",
        cascade="all, delete-orphan",
        order_by="desc(VoiceGeneration.created_at)",
    )

    def __repr__(self) -> str:
        return f"<Scene {self.scene_number} of project {self.project_id}>"
