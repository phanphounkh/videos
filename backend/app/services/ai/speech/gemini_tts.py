"""Gemini text-to-speech, with subtitle timing aligned by Gemini.

WHY Gemini for Khmer: its TTS models speak Khmer with natural native prosody
and take a free-text delivery direction, so each scene can be told the way the
story needs it (excited hook, whispered secret, triumphant payoff) instead of
one flat reading for the whole video.

The text is read verbatim; delivery goes in the `speech_metadata` style
annotation, never into the text, or the voice would read the direction aloud.
Audio comes back as 24 kHz WAV and is stored as MP3 like every other voice.
Duration is measured with ffprobe; word timings come from GeminiAligner.
"""

from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.services.ai.base import AudioResult, TTSProvider, WordMark
from app.services.ai.gemini import GeminiClient, response_audio
from app.services.ai.speech.gemini_aligner import GeminiAligner
from app.services.ai.speech.timing import (
    estimate_duration,
    find_pauses,
    marks_from_pauses,
    snap_to_pauses,
    speech_units,
)
from app.services.media import ENVELOPE_FPS, loudness_envelope, probe_duration, to_mp3

log = get_logger(__name__)

# Gemini's prebuilt voices. A project voice that names one of these is used as is.
GEMINI_VOICES = {
    "Zephyr",
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Leda",
    "Orus",
    "Aoede",
    "Callirrhoe",
    "Autonoe",
    "Enceladus",
    "Iapetus",
    "Umbriel",
    "Algieba",
    "Despina",
    "Erinome",
    "Algenib",
    "Rasalgethi",
    "Laomedeia",
    "Achernar",
    "Alnilam",
    "Schedar",
    "Gacrux",
    "Pulcherrima",
    "Achird",
    "Zubenelgenubi",
    "Vindemiatrix",
    "Sadachbia",
    "Sadaltager",
    "Sulafat",
}
VOICE_ALIASES = {"male": "Puck", "female": "Kore"}

LANGUAGE_NAMES = {"km": "Khmer (Cambodian)", "en": "English", "th": "Thai", "vi": "Vietnamese"}


class GeminiTTSProvider(TTSProvider):
    name = "gemini-tts"

    def __init__(
        self, client: GeminiClient | None = None, aligner: GeminiAligner | None = None
    ) -> None:
        self._client = client or GeminiClient()
        self._aligner = aligner or GeminiAligner(self._client)
        settings = get_settings()
        self._model = settings.gemini_tts_model
        self._default_voice = settings.gemini_tts_voice
        self._base_style = settings.gemini_tts_style

    def supports_language(self, language: str) -> bool:
        # Gemini TTS detects the language from the text and covers Khmer.
        return True

    def resolve_voice(self, voice: str) -> str:
        requested = (voice or "").strip()
        if requested.lower() in VOICE_ALIASES:
            return VOICE_ALIASES[requested.lower()]
        if requested.capitalize() in GEMINI_VOICES:
            return requested.capitalize()
        # "default", empty, or another provider's voice id (km-KH-...Neural).
        return self._default_voice

    def style_for(self, language: str, style: str | None) -> str:
        key = (language or "en").lower().split("-")[0]
        parts = [f"Speak in {LANGUAGE_NAMES.get(key, key)}", self._base_style]
        if style and style.strip():
            parts.append(f"for this moment: {style.strip()}")
        return "; ".join(parts)

    def request_body(
        self, text: str, language: str, voice: str, style: str | None
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "input": [
                {
                    "type": "user_input",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                            "annotations": [
                                {
                                    "type": "speech_metadata",
                                    "style": self.style_for(language, style),
                                }
                            ],
                        }
                    ],
                }
            ],
            "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": self.resolve_voice(voice)}]},
        }

    async def generate(
        self, text: str, language: str, voice: str, *, style: str | None = None
    ) -> AudioResult:
        clean = text.strip()
        if not clean:
            raise ProviderError("There is no text to speak.", code="TTS_EMPTY_TEXT")

        body = self.request_body(clean, language, voice, style)
        payload = await self._client.interact(body)
        raw, mime_type = response_audio(payload)
        try:
            data = await to_mp3(raw, mime_type)
        except RuntimeError as exc:
            raise ProviderError(str(exc), code="TTS_PROVIDER_ERROR") from exc

        measured = await probe_duration(data)
        if measured is None:
            log.warning("tts_duration_estimated", provider=self.name, chars=len(clean))
        duration = measured or estimate_duration(clean, language=language)

        # Subtitle timing: Gemini says which phrase is where, the audio's real
        # pauses fix the exact moments. Without Gemini (quota, bad answer) the
        # pauses alone time the phrases. Timing never costs us the voice.
        pauses = find_pauses(await loudness_envelope(data), ENVELOPE_FPS)
        try:
            marks = await self._aligner.align(data, "audio/mp3", clean, language, duration)
        except ProviderError as exc:
            log.warning("gemini_alignment_skipped", error=exc.message)
            marks = []
        if marks:
            timed = snap_to_pauses([(m.text, m.start, m.end) for m in marks], pauses)
            timing = "gemini"
        else:
            timed = marks_from_pauses(
                speech_units(clean, language=language), pauses, duration, language=language
            )
            timing = "pauses"
        marks = [WordMark(text, start, end) for text, start, end in timed]

        resolved = body["generation_config"]["speech_config"][0]["voice"]
        log.info(
            "voice_generation_completed",
            provider=self.name,
            voice=resolved,
            language=language,
            duration=duration,
            marks=len(marks),
            timing=timing,
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
