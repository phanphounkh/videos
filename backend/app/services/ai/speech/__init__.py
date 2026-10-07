"""Speech providers: text-to-speech and speech-to-text.

The architecture is per-language on purpose. `get_tts_provider(language)` can
return a Khmer engine for "km" and a different engine for everything else, which
is exactly how Khmer narration will be added without touching callers.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.services.ai.base import TTSProvider
from app.services.ai.speech.silent_tts import SilentTTSProvider
from app.services.ai.speech.timing import (
    distribute_timings,
    estimate_duration,
    is_khmer,
    khmer_clusters,
    split_into_segments,
)

__all__ = [
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


def get_tts_provider(language: str = "en") -> TTSProvider:
    """Resolve a TTS provider for a language.

    Today every language resolves to the silent mock. The hook for Khmer-specific
    routing is already here: add a KhmerTTSProvider and return it for "km".
    """
    configured = get_settings().tts_provider
    if configured == "mock":
        return _mock_provider()
    raise ProviderError(
        f"TTS_PROVIDER={configured} is not implemented yet. Use TTS_PROVIDER=mock.",
        code="PROVIDER_NOT_IMPLEMENTED",
    )
