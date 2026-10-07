"""Caption: one timed subtitle segment inside a scene.

Times are seconds relative to the START OF THE SCENE, not of the video. That way
reordering or retiming a scene does not require rewriting every caption row.

Khmer note: a segment is whatever the caption builder produced. We never assume
space-separated words, because Khmer does not use spaces between words.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.scene import Scene


class Caption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "captions"

    scene_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)

    scene: Mapped["Scene"] = relationship(back_populates="captions")

    def __repr__(self) -> str:
        return f"<Caption {self.start_time:.2f}-{self.end_time:.2f} {self.text[:24]!r}>"
