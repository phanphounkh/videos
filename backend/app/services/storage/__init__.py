"""Object storage: bytes live here, the database only stores keys."""

from app.services.storage.base import (
    StorageBackend,
    StoredObject,
    project_upload_key,
    render_key,
    scene_image_key,
    scene_upload_key,
    scene_voice_key,
    thumbnail_key,
)
from app.services.storage.s3 import get_storage
from app.services.storage.urls import public_url

__all__ = [
    "StorageBackend",
    "StoredObject",
    "get_storage",
    "project_upload_key",
    "public_url",
    "render_key",
    "scene_image_key",
    "scene_upload_key",
    "scene_voice_key",
    "thumbnail_key",
]
