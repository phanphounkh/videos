"""User response schema (never exposes the password hash)."""

import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class UserResponse(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool = False
    plan: str = "free"
    avatar_url: str | None = None
    created_at: datetime
