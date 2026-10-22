"""Caption building, shared by the scene editor and the generation pipeline.

Captions are timed to the speech marks stored with the scene's voice (see
`speech_settings`) while the narration still matches what was spoken; otherwise
timings are estimated from text length.

WHY its own module: captions are derived data - whenever narration, duration or
language changes they must be rebuilt. One implementation means the editor and
the AI pipeline can never disagree about segmentation or timing.

IMPLEMENTATION NOTE: this deliberately uses an explicit DELETE statement and
`session.add()` instead of assigning to `scene.captions`. Assigning to a
relationship collection makes SQLAlchemy load the old collection first, and if
it is not already loaded that lazy load happens outside the async greenlet
context and raises MissingGreenlet. The collection is expired afterwards so the
next read returns the new rows.
"""

from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.caption import Caption
from app.models.scene import Scene
from app.services.ai.speech import (
    captions_from_marks,
    distribute_timings,
    split_into_segments,
)

# Key in `Scene.settings` holding what the voice generator measured.
SPEECH_SETTINGS_KEY = "speech"
# Set when the user edited the captions by hand (see CaptionService.replace).
CAPTIONS_EDITED_KEY = "captions_edited"
MAX_CAPTION_CHARS = 300
MIN_CAPTION_SECONDS = 0.1


def speech_settings(scene: Scene) -> dict[str, Any] | None:
    """The scene's stored speech data, if it still describes the narration.

    Editing the narration makes the old marks wrong (and the audio stale), so
    they are only trusted while the text is unchanged.
    """
    speech = (scene.settings or {}).get(SPEECH_SETTINGS_KEY)
    if not isinstance(speech, dict) or speech.get("narration") != scene.narration:
        return None
    return speech


class CaptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def rebuild(self, scene: Scene, duration: float | None = None) -> int:
        """Replaces a scene's captions. Returns how many segments were written."""
        await self.session.execute(delete(Caption).where(Caption.scene_id == scene.id))

        language = scene.language or "en"
        total = duration if duration is not None else scene.duration
        speech = speech_settings(scene)
        if speech and speech.get("words"):
            words = [(str(text), float(start), float(end)) for text, start, end in speech["words"]]
            timings = captions_from_marks(words, total, language=language)
        else:
            segments = split_into_segments(scene.narration, language=language)
            timings = distribute_timings(segments, total, language=language)

        for index, (text, start, end) in enumerate(timings):
            self.session.add(
                Caption(
                    scene_id=scene.id,
                    segment_index=index,
                    text=text,
                    start_time=start,
                    end_time=end,
                    language=language,
                )
            )

        await self.session.flush()
        # The in-memory collection is now stale (rows were deleted behind the
        # ORM's back); expire it so the next access re-reads from the database.
        self.session.expire(scene, ["captions"])
        # Rebuilt from the narration and voice: no longer hand-edited.
        if (scene.settings or {}).get(CAPTIONS_EDITED_KEY):
            scene.settings = {
                k: v for k, v in scene.settings.items() if k != CAPTIONS_EDITED_KEY
            }
        return len(timings)

    async def replace(self, scene: Scene, items: list[tuple[str, float, float]]) -> int:
        """Writes hand-edited captions and remembers that they are hand-edited.

        Validation lives here, next to the data: text present, inside the scene,
        in order, and never overlapping (the renderer shows one caption at a time,
        so an overlap would silently hide one of them).
        """
        ordered = sorted(items, key=lambda item: item[1])
        cleaned: list[tuple[str, float, float]] = []
        for text, start, end in ordered:
            text = text.strip()
            if not text:
                raise ValidationError("A caption cannot be empty.", code="EMPTY_CAPTION")
            if len(text) > MAX_CAPTION_CHARS:
                raise ValidationError(
                    f"A caption can be at most {MAX_CAPTION_CHARS} characters.",
                    code="CAPTION_TOO_LONG",
                )
            if start >= scene.duration - 0.05:
                raise ValidationError(
                    f"A caption starting at {start:.2f}s is past the end of the "
                    f"{scene.duration:.2f}s scene.",
                    code="CAPTION_OUT_OF_RANGE",
                )
            end = min(end, scene.duration)
            if end - start < MIN_CAPTION_SECONDS:
                raise ValidationError(
                    f"A caption must last at least {MIN_CAPTION_SECONDS}s.",
                    code="CAPTION_TOO_SHORT",
                )
            if cleaned and start < cleaned[-1][2] - 0.01:
                raise ValidationError(
                    "Captions cannot overlap: one must end before the next begins.",
                    code="CAPTIONS_OVERLAP",
                )
            cleaned.append((text, round(start, 3), round(end, 3)))

        await self._write(scene, cleaned)
        scene.settings = {**(scene.settings or {}), CAPTIONS_EDITED_KEY: True}
        return len(cleaned)

    async def clamp(self, scene: Scene) -> None:
        """After a length change: hand-edited captions keep their times, but must
        not extend past the new end of the scene."""
        kept: list[tuple[str, float, float]] = []
        for caption in scene.captions:
            if caption.start_time >= scene.duration - 0.05:
                continue
            end = min(caption.end_time, scene.duration)
            if end - caption.start_time >= 0.05:
                kept.append((caption.text, caption.start_time, end))
        await self._write(scene, kept)

    async def _write(self, scene: Scene, items: list[tuple[str, float, float]]) -> None:
        await self.session.execute(delete(Caption).where(Caption.scene_id == scene.id))
        language = scene.language or "en"
        for index, (text, start, end) in enumerate(items):
            self.session.add(
                Caption(
                    scene_id=scene.id,
                    segment_index=index,
                    text=text,
                    start_time=start,
                    end_time=end,
                    language=language,
                )
            )
        await self.session.flush()
        self.session.expire(scene, ["captions"])
