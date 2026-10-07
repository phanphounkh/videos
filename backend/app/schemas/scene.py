"""Scene and caption schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Transition
from app.schemas.common import ORMModel


class CaptionResponse(ORMModel):
    id: uuid.UUID
    segment_index: int
    text: str
    start_time: float
    end_time: float
    language: str


class CaptionInput(BaseModel):
    text: str = Field(min_length=1)
    start_time: float = Field(ge=0)
    end_time: float = Field(gt=0)

    @model_validator(mode="after")
    def _end_after_start(self) -> "CaptionInput":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class SceneCreateRequest(BaseModel):
    narration: str = Field(default="", max_length=5000)
    visual_prompt: str | None = Field(default=None, max_length=2000)
    on_screen_text: str | None = Field(default=None, max_length=500)
    duration: float = Field(default=5.0, gt=0, le=120)
    transition: Transition = Transition.FADE
    background_color: str = Field(default="#0b0d12", max_length=16)
    language: str | None = Field(default=None, max_length=16)
    settings: dict[str, Any] = Field(default_factory=dict)
    # Insert position (1-based). Omitted => appended to the end.
    scene_number: int | None = Field(default=None, ge=1)


class SceneUpdateRequest(BaseModel):
    narration: str | None = Field(default=None, max_length=5000)
    visual_prompt: str | None = Field(default=None, max_length=2000)
    on_screen_text: str | None = Field(default=None, max_length=500)
    duration: float | None = Field(default=None, gt=0, le=120)
    transition: Transition | None = None
    background_color: str | None = Field(default=None, max_length=16)
    language: str | None = Field(default=None, max_length=16)
    settings: dict[str, Any] | None = None


class SceneReorderRequest(BaseModel):
    """Full ordered list of scene ids. Partial lists are rejected, because a
    partial reorder cannot be applied unambiguously."""

    scene_ids: list[uuid.UUID] = Field(min_length=1)


class SceneResponse(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    scene_number: int
    narration: str
    visual_prompt: str | None
    on_screen_text: str | None
    duration: float
    start_time: float
    transition: str
    background_color: str
    language: str | None
    settings: dict[str, Any]
    image_url: str | None
    audio_url: str | None
    video_url: str | None
    captions: list[CaptionResponse]
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(BaseModel):
    """A project plus its scenes - what the editor loads in one request."""

    project: Any
    scenes: list[SceneResponse]
