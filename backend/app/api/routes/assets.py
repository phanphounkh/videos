"""Asset endpoints: upload your own media, inspect metadata.

Upload security (requirement #17), all enforced before a single byte is stored:
  - size limit, checked against the real body length, not the Content-Length header
  - MIME allow-list, derived from the file extension AND the declared type
  - filename sanitisation - the client's filename never becomes a storage path
  - project ownership check
"""

import mimetypes
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.dependencies import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.asset import Asset
from app.models.enums import AssetSource, AssetType
from app.repositories.asset_repository import AssetRepository
from app.schemas.asset import AssetResponse
from app.services.project_service import ProjectService
from app.services.scene_service import SceneService
from app.services.storage import get_storage, project_upload_key, scene_upload_key
from app.services.storage.urls import public_url

router = APIRouter(prefix="/assets", tags=["assets"])
log = get_logger(__name__)

ALLOWED_MIME_TYPES: dict[str, AssetType] = {
    "image/png": AssetType.IMAGE,
    "image/jpeg": AssetType.IMAGE,
    "image/webp": AssetType.IMAGE,
    "video/mp4": AssetType.VIDEO,
    "video/webm": AssetType.VIDEO,
    "audio/mpeg": AssetType.AUDIO,
    "audio/wav": AssetType.AUDIO,
    "audio/x-wav": AssetType.AUDIO,
    "audio/mp4": AssetType.AUDIO,
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    """Strips directories and unsafe characters: 'a/../b .png' -> 'b_.png'."""
    base = name.replace("\\", "/").split("/")[-1]
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or "upload"
    return cleaned[:120]


def _to_response(asset: Asset) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        project_id=asset.project_id,
        scene_id=asset.scene_id,
        type=asset.type,
        source=asset.source,
        storage_key=asset.storage_key,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        duration=asset.duration,
        width=asset.width,
        height=asset.height,
        original_filename=asset.original_filename,
        provider=asset.provider,
        url=public_url(asset.storage_key),
        created_at=asset.created_at,
    )


@router.post("/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    current_user: CurrentUser,
    session: SessionDep,
    project_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
    scene_id: Annotated[uuid.UUID | None, Form()] = None,
    attach: Annotated[bool, Form()] = True,
) -> AssetResponse:
    settings = get_settings()
    project = await ProjectService(session).get(project_id, current_user.id)

    scene = None
    if scene_id is not None:
        scene = await SceneService(session).get_owned(scene_id, current_user.id)
        if scene.project_id != project.id:
            raise ValidationError("That scene belongs to a different project.",
                                  code="SCENE_PROJECT_MISMATCH")

    filename = safe_filename(file.filename or "upload")
    declared = (file.content_type or "").split(";")[0].strip().lower()
    guessed = (mimetypes.guess_type(filename)[0] or "").lower()
    mime_type = declared if declared in ALLOWED_MIME_TYPES else guessed

    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported file type: {declared or guessed or 'unknown'}.",
            code="UNSUPPORTED_MEDIA_TYPE",
            details={"allowed": sorted(ALLOWED_MIME_TYPES)},
        )

    # Read with a hard cap: never trust Content-Length, and never buffer an
    # unbounded upload into memory.
    limit = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise ValidationError(
            f"File is larger than the {settings.max_upload_size_mb} MB limit.",
            code="FILE_TOO_LARGE",
        )
    if not data:
        raise ValidationError("The uploaded file is empty.", code="EMPTY_FILE")

    asset_type = ALLOWED_MIME_TYPES[mime_type]
    unique = f"{uuid.uuid4().hex[:8]}-{filename}"
    key = (
        scene_upload_key(str(project.id), str(scene.id), unique)
        if scene is not None
        else project_upload_key(str(project.id), unique)
    )
    stored = await get_storage().put_bytes(key, data, mime_type)

    asset = Asset(
        project_id=project.id,
        scene_id=scene.id if scene else None,
        type=asset_type,
        source=AssetSource.UPLOADED,
        storage_key=stored.storage_key,
        mime_type=mime_type,
        size_bytes=stored.size_bytes,
        original_filename=filename,
        provider="upload",
    )
    session.add(asset)
    await session.flush()

    # Attach the upload to the scene so it is used by the renderer right away.
    if scene is not None and attach:
        if asset_type == AssetType.IMAGE:
            scene.image_asset_id = asset.id
        elif asset_type == AssetType.VIDEO:
            scene.video_asset_id = asset.id
        elif asset_type == AssetType.AUDIO:
            scene.audio_asset_id = asset.id

    await session.commit()
    log.info("asset_uploaded", asset_id=str(asset.id), type=asset_type, size=len(data))
    return _to_response(asset)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> AssetResponse:
    asset = await AssetRepository(session).get(asset_id)
    if asset is None:
        raise NotFoundError("Asset was not found.", code="ASSET_NOT_FOUND")
    # Ownership is checked through the asset's project.
    await ProjectService(session).get(asset.project_id, current_user.id)
    return _to_response(asset)


@router.get("/{asset_id}/download-url", response_model=dict[str, str])
async def get_download_url(
    asset_id: uuid.UUID, current_user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    """A time-limited presigned URL, for private buckets."""
    asset = await AssetRepository(session).get(asset_id)
    if asset is None:
        raise NotFoundError("Asset was not found.", code="ASSET_NOT_FOUND")
    await ProjectService(session).get(asset.project_id, current_user.id)
    url = await get_storage().presigned_url(asset.storage_key, expires_in=3600)
    return {"url": url, "expires_in": "3600"}
