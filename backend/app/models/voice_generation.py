"""VoiceGeneration: the audit trail of one TTS attempt for a scene.

WHY a separate table instead of a column on Scene: TTS calls cost money, fail,
and get retried with different voices. Keeping every attempt lets us show a
history, retry only what failed, and never lose an error message.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GenerationStatus

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.scene import Scene


class VoiceGeneration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "voice_generations"

    scene_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    voice: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(32), default=GenerationStatus.PENDING, nullable=False
    )
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    scene: Mapped["Scene"] = relationship(back_populates="voice_generations")
    asset: Mapped["Asset | None"] = relationship(foreign_keys=[asset_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<VoiceGeneration {self.provider}/{self.voice} {self.status}>"
