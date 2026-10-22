"""Domain enumerations shared by models and schemas.

These are stored as VARCHAR with a CHECK-like validation at the application
layer rather than as native PostgreSQL ENUM types, because altering a PG enum
requires a migration with downtime-prone DDL, and we will add statuses often.
"""

from enum import StrEnum


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class AspectRatio(StrEnum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"

    @property
    def dimensions(self) -> tuple[int, int]:
        return {
            AspectRatio.LANDSCAPE: (1920, 1080),
            AspectRatio.PORTRAIT: (1080, 1920),
            AspectRatio.SQUARE: (1080, 1080),
        }[self]


class VideoStyle(StrEnum):
    EDUCATIONAL = "educational"
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    SOCIAL_MEDIA = "social_media"
    MINIMAL = "minimal"
    TECHNOLOGY = "technology"
    STORYTELLING = "storytelling"


class VideoPurpose(StrEnum):
    """What the video is for. Picks the script structure, layout and defaults."""

    STORY = "story"
    PRODUCT_DEMO = "product_demo"
    SOCIAL_POST = "social_post"
    CREATOR = "creator"
    EXPLAINER = "explainer"


class AssetType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    MUSIC = "music"
    THUMBNAIL = "thumbnail"
    RENDER = "render"


class AssetSource(StrEnum):
    GENERATED = "generated"
    UPLOADED = "uploaded"
    STOCK = "stock"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RenderStatus(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RENDERING = "rendering"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class Transition(StrEnum):
    NONE = "none"
    FADE = "fade"
    SLIDE = "slide"
