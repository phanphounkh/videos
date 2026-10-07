"""Asset: metadata for one file stored in object storage.

The database NEVER holds the bytes. It holds the storage key plus metadata, so
rows stay tiny and the file can be streamed or presigned directly from MinIO/S3.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssetSource

if TYPE_CHECKING:
    from app.models.project import Project


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: project-level assets (final render, thumbnail) belong to no scene.
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), default=AssetSource.GENERATED, nullable=False)

    # e.g. projects/{project_id}/scenes/{scene_id}/image.png
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(
        back_populates="assets", foreign_keys=[project_id]
    )

    def __repr__(self) -> str:
        return f"<Asset {self.type} {self.storage_key}>"
