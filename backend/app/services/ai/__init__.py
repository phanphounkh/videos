"""AI provider layer.

Routes never import a concrete provider. They call application services, which
resolve a provider through these factories, which read configuration. That is the
whole dependency direction:

    routes -> services -> provider interface -> concrete provider
"""

from app.services.ai.base import (
    AudioResult,
    ImageProvider,
    ImageResult,
    LLMProvider,
    ScriptRequest,
    STTProvider,
    TranscriptResult,
    TranscriptSegment,
    TTSProvider,
    VideoProvider,
)
from app.services.ai.image import get_image_provider
from app.services.ai.llm import get_llm_provider
from app.services.ai.speech import get_tts_provider

__all__ = [
    "AudioResult",
    "ImageProvider",
    "ImageResult",
    "LLMProvider",
    "STTProvider",
    "ScriptRequest",
    "TTSProvider",
    "TranscriptResult",
    "TranscriptSegment",
    "VideoProvider",
    "get_image_provider",
    "get_llm_provider",
    "get_tts_provider",
]
