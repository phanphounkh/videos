"""Schemas for AI generation - including the strict contract the LLM must meet.

This file is the single most important validation boundary in the project: the
LLM is a text generator, not an API. It can return prose, markdown fences,
missing fields, wrong types or 40 scenes when we asked for 8. Nothing downstream
touches its output until it has passed through `GeneratedScript`.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import AspectRatio, Transition, VideoStyle

MAX_SCENES = 40
MIN_SCENE_DURATION = 1.0
MAX_SCENE_DURATION = 60.0


class GenerateRequest(BaseModel):
    """What the user sends from the prompt page."""

    prompt: str = Field(min_length=3, max_length=2000)
    duration: int = Field(default=60, ge=10, le=600)
    language: str = Field(default="en", max_length=16)
    style: VideoStyle = VideoStyle.EDUCATIONAL
    aspect_ratio: AspectRatio | None = None
    tone: str | None = Field(default=None, max_length=64)
    audience: str | None = Field(default=None, max_length=128)
    voice: str | None = Field(default=None, max_length=64)
    # Whether to immediately queue image + voice generation for every scene.
    generate_media: bool = True


class GeneratedScene(BaseModel):
    """One scene as produced by the LLM."""

    scene_number: int = Field(ge=1)
    narration: str = Field(min_length=1, max_length=5000)
    visual_prompt: str = Field(min_length=1, max_length=2000)
    on_screen_text: str | None = Field(default=None, max_length=500)
    duration: float = Field(ge=MIN_SCENE_DURATION, le=MAX_SCENE_DURATION)
    transition: Transition = Transition.FADE

    @field_validator("narration", "visual_prompt", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("transition", mode="before")
    @classmethod
    def _tolerate_unknown_transition(cls, value: Any) -> Any:
        """An unknown transition name must not fail the whole generation."""
        if isinstance(value, str) and value.lower() not in set(Transition):
            return Transition.FADE
        return value


class GeneratedScript(BaseModel):
    """The complete structured script. Anything that fails here is rejected."""

    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=5000)
    language: str = Field(default="en", max_length=16)
    estimated_duration: float = Field(default=0, ge=0)
    scenes: list[GeneratedScene] = Field(min_length=1, max_length=MAX_SCENES)

    @model_validator(mode="after")
    def _normalise(self) -> "GeneratedScript":
        # Renumber defensively: LLMs regularly emit 1,2,2,4 or start at 0.
        for position, scene in enumerate(self.scenes, start=1):
            scene.scene_number = position
        if not self.estimated_duration:
            self.estimated_duration = round(sum(s.duration for s in self.scenes), 2)
        return self

    @property
    def total_duration(self) -> float:
        return round(sum(scene.duration for scene in self.scenes), 2)


class GenerateResponse(BaseModel):
    project_id: uuid.UUID
    title: str
    status: str
    scene_count: int
    duration: float
    # Present when media generation was queued, so the client can poll.
    media_jobs_queued: int = 0


class SceneMediaResponse(BaseModel):
    scene_id: uuid.UUID
    asset_id: uuid.UUID | None
    url: str | None
    status: str
    provider: str
    message: str | None = None
