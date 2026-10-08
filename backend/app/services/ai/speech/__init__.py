"""Speech providers: text-to-speech and speech-to-text.

Provider selection is PER LANGUAGE on purpose, which is how Khmer gets its own
engine without any caller changing:

    get_tts_provider("km")  ->  a provider that actually speaks Khmer
    get_tts_provider("en")  ->  the configured default

`TTS_PROVIDER=edge` is the real default (Microsoft Edge neural voices, no API
key, includes Khmer). `TTS_PROVIDER=mock` produces silent audio of the correct
duration and is useful offline or in tests.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.services.ai.base import TTSProvider
from app.services.ai.speech.edge_tts_provider import EdgeTTSProvider
from app.services.ai.speech.silent_tts import SilentTTSProvider
from app.services.ai.speech.timing import (
    distribute_timings,
    estimate_duration,
    is_khmer,
    khmer_clusters,
    split_into_segments,
)

log = get_logger(__name__)

__all__ = [
    "EdgeTTSProvider",
    "SilentTTSProvider",
    "TTSProvider",
    "distribute_timings",
    "estimate_duration",
    "get_tts_provider",
    "is_khmer",
    "khmer_clusters",
    "split_into_segments",
]


@lru_cache
def _mock_provider() -> TTSProvider:
    return SilentTTSProvider()


@lru_cache
def _edge_provider() -> TTSProvider:
    return EdgeTTSProvider()


def get_tts_provider(language: str = "en") -> TTSProvider:
    """Resolve a TTS provider for a language.

    If the configured provider cannot speak the requested language we fall back
    to the silent provider rather than producing confident nonsense in the wrong
    language - and we log it, so it is visible rather than mysterious.
    """
    configured = get_settings().tts_provider

    if configured == "mock":
        return _mock_provider()

    if configured == "edge":
        provider = _edge_provider()
        if provider.supports_language(language):
            return provider
        log.warning("tts_language_unsupported", provider=provider.name, language=language)
        return _mock_provider()

    raise ProviderError(
        f"TTS_PROVIDER={configured} is not implemented. Use 'edge' or 'mock'.",
        code="PROVIDER_NOT_IMPLEMENTED",
    )
