"""Subtitle timing from Gemini: when is each part of the narration spoken?

WHY: Gemini TTS returns audio without word timings, and captions guessed from
text length drift badly in Khmer, where phrase length and speaking time do not
match well. Gemini can listen to the audio it just produced, so we give it the
EXACT narration, pre-split into numbered units, and ask only for each unit's
start and end. It never rewrites the text - captions always show the script
exactly as written.

The answer is validated (every unit present, times ordered and inside the
audio, speech actually covered). A failed check is retried once; after that
(or when the quota is used up) the caller falls back to timing from the
audio's own pauses rather than trusting bad answers.
"""

import base64
import json
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.services.ai.base import WordMark
from app.services.ai.gemini import GeminiClient, response_text
from app.services.ai.llm.parsing import extract_json_object
from app.services.ai.speech.timing import speech_units

log = get_logger(__name__)

ATTEMPTS = 2

_SCHEMA = {
    "type": "object",
    "properties": {
        "units": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "start": {"type": "number", "description": "seconds, 2 decimals"},
                    "end": {"type": "number", "description": "seconds, 2 decimals"},
                },
                "required": ["index", "start", "end"],
            },
        }
    },
    "required": ["units"],
}

_INSTRUCTION = """You are a precise forced-alignment engine for subtitles.
You receive a speech recording and its exact transcript, split into numbered units.
For EVERY unit, report when it starts and ends in the recording, in seconds with
two decimals (e.g. 1.37), measured from the start of the audio.
Rules: keep the given order; never merge, skip, rename or re-split units; a unit
starts where its first sound begins and ends where its last sound ends; pauses
belong to no unit. The transcript may be Khmer: align by listening, not by
counting characters."""


def validate_alignment(
    units: list[str], items: list[dict[str, Any]], duration: float
) -> list[WordMark] | None:
    """Turns the model's answer into marks, or None when it cannot be trusted."""
    if not units:
        return []
    by_index: dict[int, tuple[float, float]] = {}
    for item in items:
        try:
            index, start, end = int(item["index"]), float(item["start"]), float(item["end"])
        except (KeyError, TypeError, ValueError):
            return None
        by_index[index] = (start, end)
    if set(by_index) != set(range(len(units))):
        return None

    limit = duration + 0.25
    marks: list[WordMark] = []
    previous_start = -1.0
    for index, text in enumerate(units):
        start, end = by_index[index]
        if start < 0 or start > limit or end < start or end > limit + 0.5:
            return None
        if start < previous_start - 0.05:
            return None  # out of order
        start, end = min(start, duration), min(end, duration)
        if marks and marks[-1].end > start:
            marks[-1].end = start  # trim small overlaps
        marks.append(WordMark(text, round(start, 3), round(max(end, start + 0.02), 3)))
        previous_start = start

    # A collapsed answer (everything squeezed into a corner of the clip) is
    # syntactically fine but useless; require the speech to be covered.
    if duration > 1.5 and (marks[-1].end < duration * 0.6 or marks[0].start > duration * 0.5):
        return None
    return marks


class GeminiAligner:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()
        settings = get_settings()
        self._model = settings.gemini_align_model.strip() or settings.gemini_model

    def request_body(self, audio: bytes, mime_type: str, units: list[str]) -> dict[str, Any]:
        transcript = json.dumps(
            [{"index": i, "text": unit} for i, unit in enumerate(units)], ensure_ascii=False
        )
        return {
            "model": self._model,
            "system_instruction": _INSTRUCTION,
            "input": [
                {"type": "text", "text": f"Transcript units:\n{transcript}"},
                {
                    "type": "audio",
                    "data": base64.b64encode(audio).decode("ascii"),
                    "mime_type": mime_type,
                },
            ],
            "response_format": {"type": "text", "mime_type": "application/json", "schema": _SCHEMA},
        }

    async def align(
        self, audio: bytes, mime_type: str, text: str, language: str, duration: float
    ) -> list[WordMark]:
        """Marks for `text` in `audio`; empty when alignment is not trustworthy."""
        units = speech_units(text, language=language)
        if not units:
            return []
        body = self.request_body(audio, mime_type, units)
        for attempt in range(1, ATTEMPTS + 1):
            try:
                payload = await self._client.interact(body)
                items = extract_json_object(response_text(payload)).get("units") or []
            except ProviderError as exc:
                log.warning("gemini_alignment_failed", attempt=attempt, error=exc.message)
                if exc.code == "GEMINI_QUOTA_EXHAUSTED":
                    break  # retrying cannot help until the quota resets
                continue
            marks = validate_alignment(units, items, duration)
            if marks is not None:
                log.info("gemini_alignment_ok", units=len(units), duration=duration)
                return marks
            log.warning("gemini_alignment_rejected", attempt=attempt, units=len(units))
        return []
