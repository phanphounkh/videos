"""User account."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    # Only ever the bcrypt hash. The plaintext password is never stored or logged.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Can open the telemetry dashboard. Granted only from the server (see app/cli.py);
    # never from a request, and never inferred from an email address, because
    # registration does not verify email ownership.
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Label shown in the account and the admin panel; the limits below are what is enforced.
    plan: Mapped[str] = mapped_column(String(32), default="free", server_default="free")
    # Monthly caps set by an admin. None means unlimited.
    limit_ai_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_exports: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Storage cap in MB; None uses the plan's default (see services/usage.py).
    limit_storage_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Storage key of the profile picture (a small square JPEG); None shows the default avatar.
    avatar_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # The favourite host (a built-in id or "custom:<uuid>"); null = no favourite.
    avatar_default: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # With a built-in favourite: swap in the same person in the style that suits each video.
    avatar_auto: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def avatar_url(self) -> str | None:
        from app.services.storage import public_url

        return public_url(self.avatar_key)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
