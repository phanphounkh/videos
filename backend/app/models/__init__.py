"""SQLAlchemy models.

Importing every model here is REQUIRED: Alembic's autogenerate and SQLAlchemy's
relationship resolver only know about classes that have actually been imported.
"""

from app.models.asset import Asset
from app.models.base import Base
from app.models.caption import Caption
from app.models.custom_avatar import CustomAvatar
from app.models.enums import (
    AspectRatio,
    AssetSource,
    AssetType,
    GenerationStatus,
    ProjectStatus,
    RenderStatus,
    Transition,
    VideoStyle,
)
from app.models.folder import Folder
from app.models.project import Project
from app.models.render_job import RenderJob
from app.models.scene import Scene
from app.models.user import User
from app.models.voice_generation import VoiceGeneration

__all__ = [
    "Folder",
    "AspectRatio",
    "Asset",
    "AssetSource",
    "AssetType",
    "Base",
    "Caption",
    "CustomAvatar",
    "GenerationStatus",
    "Project",
    "ProjectStatus",
    "RenderJob",
    "RenderStatus",
    "Scene",
    "Transition",
    "User",
    "VideoStyle",
    "VoiceGeneration",
]
