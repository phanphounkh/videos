"""The editor's per-scene settings, stored in `Scene.settings` (JSONB).

Only the keys the editor owns are validated here; anything else in the dict
(`mood`, `delivery`, `speech`, ...) belongs to the generator and passes through
untouched. Validation exists because this dict is rendered into a video: a text
layer at x=9000 or a volume of -3 must be refused at the API, not discovered as
a broken export.

Keys
  layers        text / sticker overlays, see `Layer`. Times are seconds from the
                START OF THE SCENE, like captions, so reordering scenes never
                rewrites them.
  voice_volume  narration volume, 0..1 (default 1)
  clip_volume   volume of an uploaded video's own sound, 0..1 (default 0: muted)
  trim_start    seconds to skip at the start of the uploaded video
  audio_start   seconds to skip at the start of the narration audio (set when a
                scene is split or trimmed, so the voice stays in sync)
  media_fit     "cover" fills the frame, "contain" shows the whole picture
  ken_burns     slow zoom on still pictures (default on)
  captions_edited
                the user changed the captions by hand: a length change keeps them
                (clipped); a narration, language or voice change rebuilds them
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

MAX_LAYERS = 30
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

LayerType = Literal["text", "sticker"]
LayerAnimation = Literal["none", "pop", "fade", "slide_up", "bounce"]
MediaFit = Literal["cover", "contain"]


class Layer(BaseModel):
    """One text or sticker overlay, positioned in percent of the frame."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=64)
    type: LayerType = "text"
    # A sticker's text is an emoji (or a few); a text layer's is the words.
    text: str = Field(min_length=1, max_length=500)
    # Centre of the layer, % of frame width / height.
    x: float = Field(default=50, ge=0, le=100)
    y: float = Field(default=50, ge=0, le=100)
    # Font size as % of the frame's SHORT side, so it scales with any resolution.
    font_size: float = Field(default=6, ge=1, le=60)
    rotation: float = Field(default=0, ge=-180, le=180)
    color: str = "#ffffff"
    background: str | None = None
    weight: int = Field(default=800, ge=400, le=900)
    animation: LayerAnimation = "pop"
    start: float = Field(default=0, ge=0)
    end: float = Field(default=3, gt=0)

    @model_validator(mode="after")
    def _check(self) -> "Layer":
        if not _HEX.match(self.color):
            raise ValueError("color must look like #rrggbb")
        if self.background is not None and not _HEX.match(self.background):
            raise ValueError("background must look like #rrggbb or be null")
        if self.end <= self.start:
            raise ValueError("a layer must end after it starts")
        return self


class _Known(BaseModel):
    model_config = ConfigDict(extra="ignore")

    layers: list[Layer] = Field(default_factory=list, max_length=MAX_LAYERS)
    voice_volume: float = Field(default=1, ge=0, le=1)
    clip_volume: float = Field(default=0, ge=0, le=1)
    trim_start: float = Field(default=0, ge=0, le=36000)
    audio_start: float = Field(default=0, ge=0, le=36000)
    media_fit: MediaFit = "cover"
    ken_burns: bool = True
    captions_edited: bool = False


KNOWN_KEYS = tuple(_Known.model_fields)


def validate_scene_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Returns `settings` with the editor-owned keys validated and normalised.

    A key set to None is kept as None: the service reads that as "remove it".
    Raises ValueError (surfaced as HTTP 422) naming the offending key.
    """
    cleaned = dict(settings)
    for key in KNOWN_KEYS:
        if key not in settings or settings[key] is None:
            continue
        try:
            parsed = _Known.model_validate({key: settings[key]})
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(part) for part in first["loc"])
            raise ValueError(f"settings.{where}: {first['msg']}") from exc
        value = getattr(parsed, key)
        cleaned[key] = [layer.model_dump() for layer in value] if key == "layers" else value
    return cleaned


def merge_scene_settings(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Shallow merge; a None value in `patch` deletes the key."""
    merged = dict(current or {})
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged
