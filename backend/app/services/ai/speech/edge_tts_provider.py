"""Microsoft Edge neural TTS - a REAL text-to-speech provider.

WHAT: synthesises actual speech via the `edge-tts` package.
WHY this one first: it needs no API key and no local model (important on a
      memory-constrained machine), and - decisive for this product - it ships
      two Khmer voices, `km-KH-PisethNeural` and `km-KH-SreymomNeural`, so the
      Khmer path is real speech rather than a placeholder.
CAVEAT, stated plainly: this is Microsoft's Edge "read aloud" endpoint, not a
      contractual API. It is free and unauthenticated, which also means no SLA
      and no commercial guarantee. For production, implement another
      `TTSProvider` (ElevenLabs, Google, Azure Speech proper) - that is exactly
      what the interface is for; nothing else in the codebase changes.

The returned duration is MEASURED from the audio with ffprobe, never estimated,
so captions stay in sync with the narration. Word boundaries are requested too:
Edge reports one per word for English and one per space-separated phrase for
Khmer, which is what lets captions follow the voice instead of a guess.
"""

import asyncio

import edge_tts

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.services.ai.base import AudioResult, TTSProvider, WordMark
from app.services.ai.speech.timing import estimate_duration
from app.services.media import probe_duration

log = get_logger(__name__)

# Default voice per language. Keys are matched on the language prefix, so "km"
# covers "km-KH".
DEFAULT_VOICES: dict[str, str] = {
    "km": "km-KH-PisethNeural",
    "en": "en-US-AriaNeural",
    "th": "th-TH-PremwadeeNeural",
    "vi": "vi-VN-HoaiMyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}
FALLBACK_VOICE = "en-US-AriaNeural"

# Friendly aliases so the UI can offer "male"/"female" without knowing voice ids.
VOICE_ALIASES: dict[tuple[str, str], str] = {
    ("km", "male"): "km-KH-PisethNeural",
    ("km", "female"): "km-KH-SreymomNeural",
    ("en", "male"): "en-US-GuyNeural",
    ("en", "female"): "en-US-AriaNeural",
}

MAX_ATTEMPTS = 3

# Edge reports offsets and durations in 100-nanosecond ticks.
TICKS_PER_SECOND = 10_000_000


class EdgeTTSProvider(TTSProvider):
    name = "edge-tts"

    def supports_language(self, language: str) -> bool:
        return self._language_key(language) in DEFAULT_VOICES

    async def generate(
        self, text: str, language: str, voice: str, *, style: str | None = None
    ) -> AudioResult:
        clean = text.strip()
        if not clean:
            raise ProviderError("There is no text to speak.", code="TTS_EMPTY_TEXT")

        resolved = self._resolve_voice(language, voice)
        settings = get_settings()

        last_error = "unknown error"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                data, marks = await self._synthesize(
                    clean, resolved, settings.tts_rate, settings.tts_volume
                )
            except Exception as exc:  # noqa: BLE001 - the SDK raises many types
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(2**attempt)
                continue

            if not data:
                last_error = "the provider returned no audio"
                continue

            # Measure the real length. The estimate is only a last resort, and
            # it is logged loudly: a wrong duration clips the narration at the
            # scene boundary, which is hard to notice and hard to explain.
            measured = await probe_duration(data)
            if measured is None:
                log.warning("tts_duration_estimated", provider=self.name, chars=len(clean))
            duration = measured or estimate_duration(clean, language=language)
            log.info(
                "voice_generation_completed",
                provider=self.name,
                voice=resolved,
                language=language,
                duration=duration,
                bytes=len(data),
            )
            return AudioResult(
                data=data,
                mime_type="audio/mpeg",
                duration=duration,
                provider=self.name,
                voice=resolved,
                is_placeholder=False,
                marks=marks,
            )

        raise ProviderError(
            f"Edge TTS failed after {MAX_ATTEMPTS} attempts: {last_error}",
            code="TTS_PROVIDER_ERROR",
        )

    @staticmethod
    async def _synthesize(
        text: str, voice: str, rate: str, volume: str
    ) -> tuple[bytes, list[WordMark]]:
        communicate = edge_tts.Communicate(
            text=text, voice=voice, rate=rate, volume=volume, boundary="WordBoundary"
        )
        chunks = bytearray()
        marks: list[WordMark] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk.get("data"):
                chunks.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary" and chunk.get("text"):
                start = chunk["offset"] / TICKS_PER_SECOND
                end = start + chunk["duration"] / TICKS_PER_SECOND
                marks.append(WordMark(chunk["text"], round(start, 3), round(end, 3)))
        return bytes(chunks), marks

    @staticmethod
    def _language_key(language: str) -> str:
        return (language or "en").strip().lower().split("-")[0]

    def _resolve_voice(self, language: str, voice: str) -> str:
        """Accepts a full voice id, a 'male'/'female' alias, or nothing."""
        key = self._language_key(language)
        requested = (voice or "").strip()

        # A full Edge voice id ("km-KH-SreymomNeural") is used as given.
        if requested and requested.count("-") >= 2:
            return requested

        alias = VOICE_ALIASES.get((key, requested.lower()))
        if alias:
            return alias

        return DEFAULT_VOICES.get(key, FALLBACK_VOICE)
