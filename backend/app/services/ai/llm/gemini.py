"""Gemini story writer.

Two passes for Khmer quality:
  1. draft  - the story itself, as structured JSON (same contract as OpenRouter);
  2. review - a native-Khmer editor pass over the draft that fixes spelling,
              stiff or translated phrasing, digits and symbols the voice would
              misread, and phrase spacing the subtitles break on. It must return
              the same structure; if it fails or changes the shape, the draft
              is kept, so the review can only improve a script, never lose one.
"""

import json
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.schemas.generation import GeneratedScript
from app.services.ai.base import LLMProvider, ScriptRequest
from app.services.ai.gemini import GeminiClient, response_text
from app.services.ai.llm.parsing import parse_script
from app.services.ai.llm.prompts import SCRIPT_JSON_SCHEMA, build_user_prompt, system_prompt

log = get_logger(__name__)

REVIEW_PROMPT = """You are a senior Khmer script editor for short videos that are
read aloud by a text-to-speech voice and shown as subtitles.

You receive a story script as JSON. Return the SAME JSON structure with the same
number of scenes, the same order, durations, transitions, moods and visual
prompts. Only improve the text of title, description, narration, on_screen_text
and delivery:
- correct Khmer spelling, subscripts (ជើង) and vowel signs; standard modern usage;
- replace stiff, translated or overly formal wording with how a Khmer storyteller
  naturally speaks, keeping the meaning and every story event;
- write digits, dates, times, amounts and symbols as Khmer words; remove emoji,
  hashtags and brackets; keep English words only for established proper names;
- separate phrases with single spaces about every three to six words and end
  sentences with ។ ? or ! so the voice pauses naturally;
- keep on_screen_text to at most 5 words and delivery a short English direction.
Do not add or remove scenes, and do not change facts."""


def gemini_schema(schema: Any) -> Any:
    """Adapts the shared JSON schema to the subset Gemini enforces.

    Nullable unions become their non-null type (an empty string means "none"
    and is normalised by the Pydantic schema). Length and item-count limits are
    left to Pydantic validation: Gemini rejects the whole request ("invalid
    argument") when the scene list carries minItems/maxItems.
    """
    if isinstance(schema, dict):
        out = {}
        for key, value in schema.items():
            if key in {"minLength", "maxLength", "minItems", "maxItems"}:
                continue
            if key == "type" and isinstance(value, list):
                non_null = [t for t in value if t != "null"]
                out[key] = non_null[0] if len(non_null) == 1 else non_null
                continue
            out[key] = gemini_schema(value)
        return out
    if isinstance(schema, list):
        return [gemini_schema(item) for item in schema]
    return schema


class GeminiLLMProvider(LLMProvider):
    name = "gemini"

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()
        settings = get_settings()
        self._model = settings.gemini_model
        self._review = settings.gemini_review_script

    def _body(self, system: str, text: str) -> dict[str, Any]:
        return {
            "model": self._model,
            "system_instruction": system,
            "input": text,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": gemini_schema(SCRIPT_JSON_SCHEMA),
            },
            "generation_config": {"thinking_level": "medium", "max_output_tokens": 32000},
        }

    def draft_body(self, request: ScriptRequest) -> dict[str, Any]:
        return self._body(
            system_prompt(request.purpose, request.presenter, request.language),
            build_user_prompt(
                prompt=request.prompt,
                duration=request.duration,
                language=request.language,
                style=request.style,
                tone=request.tone,
                audience=request.audience,
                purpose=request.purpose,
                presenter=request.presenter,
            ),
        )

    def review_body(self, draft: GeneratedScript) -> dict[str, Any]:
        return self._body(
            REVIEW_PROMPT, json.dumps(draft.model_dump(mode="json"), ensure_ascii=False)
        )

    async def generate_script(self, request: ScriptRequest) -> GeneratedScript:
        payload = await self._client.interact(self.draft_body(request), request_timeout=300.0)
        draft = parse_script(response_text(payload), fallback_language=request.language)
        log.info(
            "script_generated", provider=self.name, model=self._model, scenes=len(draft.scenes)
        )

        if not self._review or not request.language.lower().startswith("km"):
            return draft
        return await self._reviewed(draft, request.language)

    async def _reviewed(self, draft: GeneratedScript, language: str) -> GeneratedScript:
        try:
            payload = await self._client.interact(self.review_body(draft), request_timeout=300.0)
            reviewed = parse_script(response_text(payload), fallback_language=language)
        except ProviderError as exc:
            log.warning("script_review_failed", error=exc.message)
            return draft
        if not same_structure(draft, reviewed):
            log.warning(
                "script_review_changed_structure",
                before=len(draft.scenes),
                after=len(reviewed.scenes),
            )
            return draft
        log.info("script_reviewed", provider=self.name, scenes=len(reviewed.scenes))
        return reviewed


def same_structure(draft: GeneratedScript, reviewed: GeneratedScript) -> bool:
    """The review may only edit wording: scene count, timing and beats must match."""
    if len(draft.scenes) != len(reviewed.scenes):
        return False
    return all(
        a.duration == b.duration and a.transition == b.transition and a.mood == b.mood
        for a, b in zip(draft.scenes, reviewed.scenes, strict=True)
    )
