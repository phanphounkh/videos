"""Minimal client for the Gemini Interactions API, shared by every Gemini provider.

One place owns the endpoint, the API key header, retries and response parsing,
so the story writer, the voice and the subtitle aligner stay small.

API shape (POST {base}/interactions):
    request:  {"model", "input", "system_instruction"?, "response_format"?,
               "generation_config"?}
    response: {"status", "steps": [{"type": "model_output",
               "content": [{"type": "text", "text"} | {"type": "audio", "data", "mime_type"}]}]}

Parsing is deliberately tolerant (it also accepts a top-level `outputs` list and
`output_text`), because a provider changing an envelope detail should degrade
into a clear error, not a crash deep inside a worker.
"""

import asyncio
import base64
import re
import time
from collections import defaultdict, deque
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger

log = get_logger(__name__)

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
# Waiting out a rate limit is the cure, not a failure, so 429s get their own,
# larger budget that does not consume MAX_ATTEMPTS.
MAX_RATE_LIMIT_WAITS = 8
DEFAULT_RATE_LIMIT_WAIT = 30.0
# A per-minute limit asks for seconds; a per-day quota asks for hours. Waiting
# hours inside a request would freeze the worker, so beyond this we stop and
# say so, and skip that model until the quota resets.
MAX_RATE_LIMIT_WAIT_SECONDS = 90.0
_RETRY_IN = re.compile(r"retry in ([0-9.]+)\s*s", re.IGNORECASE)


class _RequestPacer:
    """Keeps each model under a requests-per-minute budget, process-wide.

    WHY: free-tier keys allow only a few requests per minute per model, and a
    long video needs dozens (a voice and an alignment per scene). Spacing
    requests up front is far cheaper than collecting 429s.
    """

    def __init__(self) -> None:
        self._sent: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def wait_turn(self, model: str, per_minute: int) -> None:
        if per_minute <= 0:
            return
        async with self._lock:
            sent = self._sent[model]
            while True:
                now = time.monotonic()
                while sent and now - sent[0] >= 60:
                    sent.popleft()
                if len(sent) < per_minute:
                    sent.append(now)
                    return
                delay = 60 - (now - sent[0]) + 0.25
                log.info("gemini_pacing", model=model, wait_seconds=round(delay, 1))
                await asyncio.sleep(delay)


_pacer = _RequestPacer()
# model -> monotonic time its daily quota is expected back.
_exhausted_until: dict[str, float] = {}


def rate_limit_wait(response: httpx.Response) -> float:
    """Seconds Gemini asks us to wait after a 429."""
    header = response.headers.get("retry-after")
    if header:
        try:
            return float(header) + 0.5
        except ValueError:
            pass
    match = _RETRY_IN.search(response.text)
    return float(match.group(1)) + 1.0 if match else DEFAULT_RATE_LIMIT_WAIT


def gemini_configured() -> bool:
    return bool(get_settings().gemini_api_key.strip())


class GeminiClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        settings = get_settings()
        if not settings.gemini_api_key.strip():
            raise ProviderError(
                "GEMINI_API_KEY is not set. Add your Gemini API key to the project "
                ".env and restart the backend and worker.",
                code="PROVIDER_NOT_CONFIGURED",
            )
        self._api_key = settings.gemini_api_key.strip()
        self._url = f"{settings.gemini_base_url.rstrip('/')}/interactions"
        self._per_minute = settings.gemini_requests_per_minute
        # Injected in tests so no request ever leaves the machine.
        self._transport = transport

    async def interact(
        self, body: dict[str, Any], *, request_timeout: float = 180.0
    ) -> dict[str, Any]:
        """POSTs one interaction and returns the completed response JSON."""
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}
        model = str(body.get("model", ""))
        last_error = "unknown error"
        attempt = 0
        rate_limited = 0
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(request_timeout), transport=self._transport
        ) as client:
            while attempt < MAX_ATTEMPTS:
                self._raise_if_exhausted(model)
                await _pacer.wait_turn(model, self._per_minute)
                try:
                    response = await client.post(self._url, json=body, headers=headers)
                except httpx.HTTPError as exc:
                    last_error = f"network error: {exc}"
                else:
                    if response.status_code == 200:
                        payload = response.json()
                        self._raise_for_failed(payload)
                        return payload
                    last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                    if response.status_code == 429 and rate_limited < MAX_RATE_LIMIT_WAITS:
                        rate_limited += 1
                        wait = rate_limit_wait(response)
                        if wait > MAX_RATE_LIMIT_WAIT_SECONDS:
                            _exhausted_until[model] = time.monotonic() + wait
                            self._raise_if_exhausted(model, detail=response.text[:300])
                        log.warning("gemini_rate_limited", model=model, wait_seconds=wait)
                        await asyncio.sleep(wait)
                        continue
                    if response.status_code not in RETRYABLE_STATUS:
                        break
                attempt += 1
                if attempt < MAX_ATTEMPTS:
                    backoff = 2**attempt
                    log.warning(
                        "gemini_retry",
                        model=model,
                        attempt=attempt,
                        backoff=backoff,
                        reason=last_error[:160],
                    )
                    await asyncio.sleep(backoff)

        raise ProviderError(f"Gemini request failed: {last_error}", code="GEMINI_PROVIDER_ERROR")

    @staticmethod
    def _raise_if_exhausted(model: str, detail: str = "") -> None:
        until = _exhausted_until.get(model)
        if until is None:
            return
        remaining = until - time.monotonic()
        if remaining <= 0:
            _exhausted_until.pop(model, None)
            return
        hours, minutes = int(remaining // 3600), int(remaining % 3600 // 60)
        log.warning("gemini_quota_exhausted", model=model, retry_in_seconds=round(remaining))
        raise ProviderError(
            f"Gemini quota for {model} is used up; it resets in about {hours}h{minutes:02d}m. "
            "Wait, or link billing to the API key's project in AI Studio for higher limits."
            + (f" ({detail})" if detail else ""),
            code="GEMINI_QUOTA_EXHAUSTED",
        )

    @staticmethod
    def _raise_for_failed(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status in {"failed", "cancelled", "incomplete"}:
            errors = payload.get("errors") or []
            message = "; ".join(str(e.get("message", e)) for e in errors if e) or status
            raise ProviderError(
                f"Gemini interaction {status}: {message}", code="GEMINI_PROVIDER_ERROR"
            )


def _content_blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Every content block the model produced, in order."""
    blocks: list[dict[str, Any]] = []
    for step in payload.get("steps") or []:
        if isinstance(step, dict) and step.get("type", "model_output") == "model_output":
            blocks.extend(b for b in step.get("content") or [] if isinstance(b, dict))
    for output in payload.get("outputs") or []:
        if isinstance(output, dict):
            blocks.append(output)
    return blocks


def response_text(payload: dict[str, Any]) -> str:
    """The model's text output, or a ProviderError when there is none."""
    texts = [
        b["text"] for b in _content_blocks(payload) if b.get("type") == "text" and b.get("text")
    ]
    text = "".join(texts) or payload.get("output_text") or ""
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("Gemini returned no text.", code="INVALID_AI_RESPONSE")
    return text


def response_audio(payload: dict[str, Any]) -> tuple[bytes, str]:
    """The last audio block as (bytes, mime type)."""
    audio = [b for b in _content_blocks(payload) if b.get("type") == "audio" and b.get("data")]
    if not audio:
        raise ProviderError("Gemini returned no audio.", code="INVALID_AI_RESPONSE")
    block = audio[-1]
    try:
        data = base64.b64decode(block["data"])
    except (ValueError, TypeError) as exc:
        raise ProviderError(
            "Gemini returned undecodable audio.", code="INVALID_AI_RESPONSE"
        ) from exc
    return data, str(block.get("mime_type") or "audio/wav")
