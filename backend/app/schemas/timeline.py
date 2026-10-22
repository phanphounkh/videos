"""A whole timeline as one value: what undo/redo saves and restores."""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import Transition
from app.schemas.project import MusicSettings
from app.schemas.scene_settings import validate_scene_settings


class CaptionSnapshot(BaseModel):
    text: str = Field(min_length=1)
    start_time: float = Field(ge=0)
    end_time: float = Field(gt=0)
    language: str = Field(default="en", max_length=16)


class SceneSnapshot(BaseModel):
    id: uuid.UUID
    narration: str = Field(default="", max_length=5000)
    visual_prompt: str | None = Field(default=None, max_length=2000)
    on_screen_text: str | None = Field(default=None, max_length=500)
    duration: float = Field(gt=0, le=120)
    transition: Transition = Transition.FADE
    background_color: str = Field(default="#0b0d12", max_length=16)
    language: str | None = Field(default=None, max_length=16)
    settings: dict[str, Any] = Field(default_factory=dict)
    image_asset_id: uuid.UUID | None = None
    video_asset_id: uuid.UUID | None = None
    audio_asset_id: uuid.UUID | None = None
    captions: list[CaptionSnapshot] = Field(default_factory=list, max_length=1000)

    @field_validator("settings")
    @classmethod
    def _check_settings(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_scene_settings(value)


class TimelineSnapshot(BaseModel):
    """Scenes in playing order, plus the music setup."""

    scenes: list[SceneSnapshot] = Field(max_length=200)
    music_asset_id: uuid.UUID | None = None
    music: MusicSettings = Field(default_factory=MusicSettings)

    @model_validator(mode="after")
    def _unique_ids(self) -> "TimelineSnapshot":
        ids = [scene.id for scene in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("a scene appears twice in the snapshot")
        return self
