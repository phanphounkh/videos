"""Text-to-video / image-to-video providers.

NOT IMPLEMENTED - deliberately. The MVP is an AI video COMPOSER: it assembles
generated images, narration, captions and animation into a video. External
text-to-video APIs can be added here later behind `VideoProvider`, and the
renderer already accepts a per-scene `video_asset`, so a clip would slot into the
existing timeline without schema changes.
"""

from app.core.exceptions import ProviderError
from app.services.ai.base import VideoProvider

__all__ = ["VideoProvider", "get_video_provider"]


def get_video_provider() -> VideoProvider:
    raise ProviderError(
        "No video-generation provider is configured. "
        "The MVP composes images, narration and captions instead.",
        code="PROVIDER_NOT_IMPLEMENTED",
    )
