"""OpenRouter LLM provider.

OpenRouter exposes many models behind one OpenAI-compatible endpoint, so a single
HTTP client can target GPT, Claude, Llama or Gemini by changing one env var.

Two reliability measures, both of which matter in production:
  - `response_format={"type": "json_object"}` asks the model for JSON natively.
    Not every model honours it, which is why parsing stays defensive.
  - bounded retries on 429/5xx with backoff; a 400 is NOT retried, because a
    malformed request will fail identically every time.
"""

import asyncio

import httpx

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.schemas.generation import GeneratedScript
from app.services.ai.base import LLMProvider, ScriptRequest
from app.services.ai.llm.parsing import parse_script
from app.services.ai.llm.prompts import SCRIPT_JSON_SCHEMA, SYSTEM_PROMPT, build_user_prompt

log = get_logger(__name__)

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


class OpenRouterLLMProvider(LLMProvider):
    name = "openrouter"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openrouter_api_key:
            raise ProviderError(
                "OPENROUTER_API_KEY is not set. Add your OpenRouter key to the "
                "project .env and restart the backend.",
                code="PROVIDER_NOT_CONFIGURED",
            )
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model
        self._base_url = settings.openrouter_base_url.rstrip("/")

    async def generate_script(self, request: ScriptRequest) -> GeneratedScript:
        body = self._request_body(request)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            # OpenRouter asks for these for attribution; harmless if unused.
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Khmer Story Studio",
        }

        last_error: str = "unknown error"
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    response = await client.post(
                        f"{self._base_url}/chat/completions", json=body, headers=headers
                    )
                except httpx.HTTPError as exc:
                    last_error = f"network error: {exc}"
                else:
                    if response.status_code == 200:
                        content = self._extract_content(response.json())
                        log.info(
                            "script_generated",
                            provider=self.name,
                            model=self._model,
                            chars=len(content),
                        )
                        return parse_script(content, fallback_language=request.language)

                    last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                    if response.status_code not in RETRYABLE_STATUS:
                        break

                if attempt < MAX_ATTEMPTS:
                    backoff = 2**attempt
                    log.warning(
                        "llm_retry", attempt=attempt, backoff=backoff, reason=last_error[:120]
                    )
                    await asyncio.sleep(backoff)

        raise ProviderError(f"OpenRouter request failed: {last_error}", code="LLM_PROVIDER_ERROR")

    def _request_body(self, request: ScriptRequest) -> dict:
        """Build a strict OpenRouter request that is easy to unit-test."""
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(
                        prompt=request.prompt,
                        duration=request.duration,
                        language=request.language,
                        style=request.style,
                        tone=request.tone,
                        audience=request.audience,
                    ),
                },
            ],
            "temperature": 0.85,
            "max_tokens": 8000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "khmer_entertainment_story",
                    "strict": True,
                    "schema": SCRIPT_JSON_SCHEMA,
                },
            },
            "provider": {"require_parameters": True},
        }

    @staticmethod
    def _extract_content(payload: dict) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "OpenRouter returned an unexpected response shape.",
                code="INVALID_AI_RESPONSE",
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("The model returned empty content.", code="INVALID_AI_RESPONSE")
        return content
