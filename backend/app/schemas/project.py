"""Project request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AspectRatio, ProjectStatus, VideoPurpose, VideoStyle
from app.schemas.common import ORMModel


class MusicSettings(BaseModel):
    """How the background music plays. The track itself is `music_asset_id`."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    # Multiplier on the built-in loudness (1 = the tuned default), so 0 mutes.
    volume: float = Field(default=1.0, ge=0, le=1)
    fade_in: float = Field(default=0.4, ge=0, le=10)
    fade_out: float = Field(default=1.0, ge=0, le=10)
    # Lower the music while someone is speaking.
    duck: bool = True


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    language: str = Field(default="km", max_length=16)
    aspect_ratio: AspectRatio = AspectRatio.PORTRAIT
    style: VideoStyle = VideoStyle.SOCIAL_MEDIA
    purpose: VideoPurpose = VideoPurpose.STORY
    # None means "the purpose's default".
    presenter: bool | None = None
    cta_text: str | None = Field(default=None, max_length=60)
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
    purpose: VideoPurpose | None = None
    presenter: bool | None = None
    cta_text: str | None = Field(default=None, max_length=60)
    tone: str | None = Field(default=None, max_length=64)
    audience: str | None = Field(default=None, max_length=128)
    voice: str | None = Field(default=None, max_length=64)
    target_duration: int | None = Field(default=None, ge=5, le=300)
    fps: int | None = Field(default=None, ge=15, le=60)
    music: MusicSettings | None = None


class ProjectResponse(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None
    prompt: str | None
    status: ProjectStatus
    language: str
    aspect_ratio: str
    style: str
    purpose: str
    presenter: bool
    cta_text: str | None
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
    music: MusicSettings
    music_asset_id: uuid.UUID | None = None
    music_url: str | None = None
    music_name: str | None = None
    music_duration: float | None = None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
