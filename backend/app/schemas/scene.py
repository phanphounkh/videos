"""Scene and caption schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import Transition
from app.schemas.common import ORMModel
from app.schemas.scene_settings import validate_scene_settings


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

    @field_validator("settings")
    @classmethod
    def _check_settings(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_scene_settings(value)


class SceneUpdateRequest(BaseModel):
    narration: str | None = Field(default=None, max_length=5000)
    visual_prompt: str | None = Field(default=None, max_length=2000)
    on_screen_text: str | None = Field(default=None, max_length=500)
    duration: float | None = Field(default=None, gt=0, le=120)
    transition: Transition | None = None
    background_color: str | None = Field(default=None, max_length=16)
    language: str | None = Field(default=None, max_length=16)
    # MERGED into the scene's settings (a key set to null is removed), so the
    # editor can change one thing without resending the speech data.
    settings: dict[str, Any] | None = None
    # Which uploaded or generated pictures/clips the scene uses; null removes it.
    image_asset_id: uuid.UUID | None = None
    video_asset_id: uuid.UUID | None = None

    @field_validator("settings")
    @classmethod
    def _check_settings(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return None if value is None else validate_scene_settings(value)


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
    image_asset_id: uuid.UUID | None = None
    video_asset_id: uuid.UUID | None = None
    audio_asset_id: uuid.UUID | None = None
    # Length of the uploaded clip, so the editor can limit trimming to it.
    video_duration: float | None = None
    captions: list[CaptionResponse]
    created_at: datetime
    updated_at: datetime


class CaptionsReplaceRequest(BaseModel):
    """The scene's complete caption list, as edited by hand. Times are seconds
    from the start of the scene."""

    captions: list[CaptionInput] = Field(max_length=300)


class SceneSplitRequest(BaseModel):
    """Cut a scene in two at `at` seconds from its start."""

    at: float = Field(gt=0)


class SceneTrimRequest(BaseModel):
    """Keep only [start, end] of the scene (seconds from its start)."""

    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def _ordered(self) -> "SceneTrimRequest":
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        return self


class ProjectDetailResponse(BaseModel):
    """A project plus its scenes - what the editor loads in one request."""

    project: Any
    scenes: list[SceneResponse]
