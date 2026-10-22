"""Pure timeline arithmetic: cutting a window out of a scene.

Splitting a scene at the playhead and trimming either end of a clip are the same
operation: keep the window [a, b] of the scene and re-express everything that
lives on the scene's clock relative to the new start. That means

  captions      times shift by -a; a caption belongs to the window when its
                midpoint does, so splitting at t gives every caption to exactly
                one side;
  narration     rebuilt from the kept captions, so each half says what it shows;
  speech marks  (word timings and mouth loudness the lip-sync reads) are cut the
                same way, so captions and the mouth stay in sync;
  layers        clipped to the window and shifted;
  audio_start / trim_start
                advance by a, so the voice and an uploaded video keep playing
                from where they were instead of restarting.

No database here, so it is easy to test exhaustively.
"""

from dataclasses import dataclass
from typing import Any

from app.core.exceptions import ValidationError

MIN_SCENE_SECONDS = 0.2
_EPSILON = 0.001
# A caption shorter than this after clipping is invisible; keep it readable.
_MIN_CAPTION = 0.05

CaptionTuple = tuple[str, float, float]


@dataclass(slots=True)
class CutResult:
    duration: float
    narration: str
    captions: list[CaptionTuple]
    settings: dict[str, Any]


def check_window(duration: float, a: float, b: float) -> None:
    if a < -_EPSILON or b > duration + _EPSILON or b - a < MIN_SCENE_SECONDS:
        raise ValidationError(
            f"The cut {a:.2f}s-{b:.2f}s must lie inside the {duration:.2f}s scene and leave "
            f"at least {MIN_SCENE_SECONDS}s.",
            code="INVALID_CUT",
        )


def cut_window(
    *,
    duration: float,
    narration: str,
    captions: list[CaptionTuple],
    settings: dict[str, Any],
    a: float,
    b: float,
) -> CutResult:
    check_window(duration, a, b)  # before clamping, so a real overshoot is an error
    a = max(0.0, a)
    b = min(duration, b)
    length = round(b - a, 3)
    whole = a <= _EPSILON and b >= duration - _EPSILON

    kept: list[CaptionTuple] = []
    for text, start, end in captions:
        if a <= (start + end) / 2 < b:
            new_start = round(max(start, a) - a, 3)
            new_end = round(min(end, b) - a, 3)
            if new_end - new_start < _MIN_CAPTION:
                new_end = round(min(length, new_start + _MIN_CAPTION), 3)
            if new_end > new_start:
                kept.append((text, new_start, new_end))

    new_narration = narration if whole else " ".join(text for text, _, _ in kept)

    new_settings = dict(settings or {})
    speech = new_settings.get("speech")
    if isinstance(speech, dict) and not whole:
        new_settings["speech"] = _cut_speech(speech, a, b, new_narration)
        if new_settings["speech"] is None:
            del new_settings["speech"]

    if a > _EPSILON:
        new_settings["audio_start"] = round(float(new_settings.get("audio_start", 0)) + a, 3)
        new_settings["trim_start"] = round(float(new_settings.get("trim_start", 0)) + a, 3)

    layers = []
    for layer in new_settings.get("layers") or []:
        start = round(max(float(layer["start"]), a) - a, 3)
        end = round(min(float(layer["end"]), b) - a, 3)
        if end - start >= _MIN_CAPTION:
            layers.append({**layer, "start": start, "end": end})
    if "layers" in new_settings:
        new_settings["layers"] = layers

    return CutResult(duration=length, narration=new_narration, captions=kept, settings=new_settings)


def _cut_speech(
    speech: dict[str, Any], a: float, b: float, narration: str
) -> dict[str, Any] | None:
    words = [
        [text, round(max(float(start), a) - a, 3), round(min(float(end), b) - a, 3)]
        for text, start, end in speech.get("words", [])
        if a <= (float(start) + float(end)) / 2 < b
    ]
    if not words:
        return None
    cut = dict(speech)
    cut["words"] = words
    cut["narration"] = narration
    mouth = speech.get("mouth")
    if isinstance(mouth, list):
        fps = int(speech.get("fps", 30)) or 30
        cut["mouth"] = mouth[round(a * fps) : round(b * fps)]
    return cut
