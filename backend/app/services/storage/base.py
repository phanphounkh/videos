"""Storage abstraction.

WHAT: the interface every storage backend implements - put bytes, get bytes,
      delete, presign, check existence.
WHY:  services upload "an object with a key"; they must not know whether that is
      MinIO, SeaweedFS, AWS S3 or Cloudflare R2. Swapping backends then means
      changing env vars, not code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class StoredObject:
    """What the caller needs after an upload, and what an Asset row stores."""

    storage_key: str
    size_bytes: int
    mime_type: str
    public_url: str


class StorageBackend(ABC):
    @abstractmethod
    async def ensure_ready(self) -> None:
        """Create the bucket if it is missing. Safe to call repeatedly."""

    @abstractmethod
    async def put_bytes(self, key: str, data: bytes, mime_type: str) -> StoredObject: ...

    @abstractmethod
    async def get_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def presigned_url(self, key: str, expires_in: int = 3600) -> str: ...


# --- storage key layout ------------------------------------------------------
# One function per kind of object so the layout is defined in exactly one place.

def scene_image_key(project_id: str, scene_id: str, ext: str = "png") -> str:
    return f"projects/{project_id}/scenes/{scene_id}/image.{ext}"


def scene_voice_key(project_id: str, scene_id: str, ext: str = "mp3") -> str:
    return f"projects/{project_id}/scenes/{scene_id}/voice.{ext}"


def scene_upload_key(project_id: str, scene_id: str, filename: str) -> str:
    return f"projects/{project_id}/scenes/{scene_id}/uploads/{filename}"


def project_upload_key(project_id: str, filename: str) -> str:
    return f"projects/{project_id}/uploads/{filename}"


def render_key(project_id: str, job_id: str) -> str:
    return f"projects/{project_id}/renders/{job_id}.mp4"


def thumbnail_key(project_id: str, job_id: str) -> str:
    return f"projects/{project_id}/renders/{job_id}-thumb.jpg"
