"""RenderJob: one attempt to turn a project into an MP4.

Progress and status live here (not on Project) because a project can be rendered
many times, and a failed render must not destroy the record of a successful one.
`logs` keeps the renderer's output so a failure is debuggable after the fact.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RenderStatus

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.project import Project


class RenderJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "render_jobs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    output_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(32), default=RenderStatus.QUEUED, nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="render_jobs")
    output_asset: Mapped["Asset | None"] = relationship(
        foreign_keys=[output_asset_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<RenderJob {self.id} {self.status} {self.progress}%>"
