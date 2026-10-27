"""CustomAvatar: a photo a person uploaded to be the on-screen host."""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CustomAvatar(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "custom_avatars"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    # A 512x512 JPEG under avatar-photos/<user_id>/.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    # "mouth": the renderer animates a mouth on the photo; "subtle": gentle motion only.
    mode: Mapped[str] = mapped_column(
        String(16), default="mouth", server_default="mouth", nullable=False
    )

    @property
    def ref(self) -> str:
        """The id every other record uses to point at this avatar."""
        return f"custom:{self.id}"

    def __repr__(self) -> str:
        return f"<CustomAvatar {self.name}>"
