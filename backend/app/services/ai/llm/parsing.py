"""Defensive parsing of LLM output.

Even with "reply with JSON only", models wrap output in ```json fences, prepend
"Here is your script:", or emit trailing commas. This module extracts the JSON
object and validates it; anything that cannot be salvaged raises a clear
ProviderError instead of corrupting the database.
"""

import json
import re
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.schemas.generation import GeneratedScript

log = get_logger(__name__)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()

    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    # Fall back to the outermost {...} span if there is still surrounding prose.
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ProviderError(
                "The model did not return a JSON object.", code="INVALID_AI_RESPONSE"
            )
        text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # One cheap repair pass: strip trailing commas, which models love.
        repaired = re.sub(r",(\s*[}\]])", r"\1", text)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"The model returned malformed JSON: {exc.msg}", code="INVALID_AI_RESPONSE"
            ) from exc

    if not isinstance(parsed, dict):
        raise ProviderError(
            "The model returned JSON that is not an object.", code="INVALID_AI_RESPONSE"
        )
    return parsed


def parse_script(raw: str, *, fallback_language: str = "en") -> GeneratedScript:
    payload = extract_json_object(raw)
    payload.setdefault("language", fallback_language)

    try:
        return GeneratedScript.model_validate(payload)
    except PydanticValidationError as exc:
        log.warning(
            "llm_script_validation_failed",
            error_count=exc.error_count(),
            first_error=str(exc.errors()[0]["loc"]) if exc.errors() else "",
        )
        raise ProviderError(
            "The model's script did not match the required structure.",
            code="INVALID_AI_RESPONSE",
            details={"errors": [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()[:8]]},
        ) from exc
