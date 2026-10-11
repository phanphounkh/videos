"""Project request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AspectRatio, ProjectStatus, VideoStyle
from app.schemas.common import ORMModel


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    language: str = Field(default="km", max_length=16)
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT
    style: VideoStyle = VideoStyle.SOCIAL_MEDIA
    tone: str | None = Field(default=None, max_length=64)
    audience: str | None = Field(default=None, max_length=128)
    voice: str | None = Field(default=None, max_length=64)
    target_duration: int = Field(default=60, ge=5, le=300)
    fps: int = Field(default=30, ge=15, le=60)


class ProjectUpdateRequest(BaseModel):
    """All fields optional: PATCH semantics. Unset fields are left untouched."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    language: str | None = Field(default=None, max_length=16)
    aspect_ratio: AspectRatio | None = None
    style: VideoStyle | None = None
    tone: str | None = Field(default=None, max_length=64)
    audience: str | None = Field(default=None, max_length=128)
    voice: str | None = Field(default=None, max_length=64)
    target_duration: int | None = Field(default=None, ge=5, le=300)
    fps: int | None = Field(default=None, ge=15, le=60)


class ProjectResponse(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None
    prompt: str | None
    status: ProjectStatus
    language: str
    aspect_ratio: str
    style: str
    tone: str | None
    audience: str | None
    voice: str | None
    target_duration: int
    fps: int
    width: int
    height: int
    duration: float
    scene_count: int
    thumbnail_url: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
