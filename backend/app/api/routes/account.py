"""The signed-in person's own account: profile, password, usage, deleting it."""

import io
import uuid
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, SessionDep
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.render_job import RenderJob
from app.schemas.account import (
    AccountDelete,
    ActivityItem,
    PasswordChange,
    ProfileUpdate,
    StorageResponse,
    UsageResponse,
)
from app.schemas.avatar import AvatarPreferences
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services import usage
from app.services.avatars import validate_choice
from app.services.storage import get_storage

router = APIRouter(prefix="/account", tags=["account"])
log = get_logger(__name__)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    payload: ProfileUpdate, user: CurrentUser, session: SessionDep
) -> UserResponse:
    user.full_name = (payload.full_name or "").strip() or None
    await session.commit()
    return UserResponse.model_validate(user)


AVATAR_SIZE = 256
AVATAR_MAX_BYTES = 5 * 1024 * 1024


def _square_jpeg(data: bytes, size: int = AVATAR_SIZE) -> bytes:
    """The upload as a 256x256 JPEG: cropped to a centred square, EXIF (location, camera)
    dropped, transparency flattened onto white. Raises ValidationError if it is not a
    picture."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            image = ImageOps.exif_transpose(source)  # respect the camera's rotation first
            if image.mode in ("RGBA", "LA", "P"):
                rgba = image.convert("RGBA")
                flat = Image.new("RGB", rgba.size, (255, 255, 255))
                flat.paste(rgba, mask=rgba.getchannel("A"))
                image = flat
            else:
                image = image.convert("RGB")
            image = ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.save(out, format="JPEG", quality=88, optimize=True)  # no exif= : none is kept
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationError(
            "That file is not a picture we can use. Try a JPG, PNG or WebP.",
            code="INVALID_IMAGE",
        ) from exc


@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    file: Annotated[UploadFile, File()], user: CurrentUser, session: SessionDep
) -> UserResponse:
    """Sets the profile picture. The file is cropped to a square and shrunk server-side."""
    data = await file.read(AVATAR_MAX_BYTES + 1)
    if len(data) > AVATAR_MAX_BYTES:
        raise ValidationError("That picture is larger than 5 MB.", code="FILE_TOO_LARGE")
    if not data:
        raise ValidationError("The uploaded file is empty.", code="EMPTY_FILE")
    jpeg = _square_jpeg(data)

    storage = get_storage()
    previous = user.avatar_key
    # A new key per upload, so browsers never show a cached older picture.
    key = f"avatars/{user.id}/{uuid.uuid4().hex[:10]}.jpg"
    await storage.put_bytes(key, jpeg, "image/jpeg")
    user.avatar_key = key
    await session.commit()
    if previous:
        try:
            await storage.delete(previous)
        except Exception as exc:  # noqa: BLE001 - an orphaned old picture is not worth failing for
            log.warning("avatar_cleanup_failed", error=str(exc)[:200])
    log.info("avatar_updated", user_id=str(user.id), bytes=len(jpeg))
    return UserResponse.model_validate(user)


@router.delete("/avatar", response_model=UserResponse)
async def remove_avatar(user: CurrentUser, session: SessionDep) -> UserResponse:
    """Back to the default avatar."""
    previous = user.avatar_key
    user.avatar_key = None
    await session.commit()
    if previous:
        try:
            await get_storage().delete(previous)
        except Exception as exc:  # noqa: BLE001
            log.warning("avatar_cleanup_failed", error=str(exc)[:200])
    return UserResponse.model_validate(user)


@router.put("/avatar-preferences", response_model=AvatarPreferences)
async def set_avatar_preferences(
    payload: AvatarPreferences, user: CurrentUser, session: SessionDep
) -> AvatarPreferences:
    """The favourite host, and whether built-in favourites are restyled per video."""
    if payload.default is not None:
        await validate_choice(session, user.id, payload.default)
    user.avatar_default = payload.default
    user.avatar_auto = payload.auto
    await session.commit()
    log.info(
        "avatar_preferences_updated",
        user_id=str(user.id),
        default=payload.default,
        auto=payload.auto,
    )
    return AvatarPreferences(default=user.avatar_default, auto=user.avatar_auto)


@router.post("/password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChange, user: CurrentUser, session: SessionDep
) -> MessageResponse:
    if not verify_password(payload.current_password, user.hashed_password):
        raise AuthenticationError("Your current password is not right.", code="WRONG_PASSWORD")
    user.hashed_password = hash_password(payload.new_password)
    await session.commit()
    log.info("password_changed", user_id=str(user.id))
    return MessageResponse(message="Password changed.")


@router.get("/usage", response_model=UsageResponse)
async def my_usage(user: CurrentUser, session: SessionDep) -> UsageResponse:
    projects = (
        await session.execute(
            select(func.count()).select_from(Project).where(Project.owner_id == user.id)
        )
    ).scalar_one()
    ready = (
        await session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.owner_id == user.id, Project.status == ProjectStatus.READY)
        )
    ).scalar_one()
    return UsageResponse(
        plan=user.plan,
        period=usage.period(),
        used=await usage.current(user.id),
        limits=usage.limits_of(user),
        projects=int(projects),
        exports_ready=int(ready),
    )


@router.get("/storage", response_model=StorageResponse)
async def my_storage(user: CurrentUser, session: SessionDep) -> StorageResponse:
    return StorageResponse(
        used_bytes=await usage.storage_used_bytes(session, user.id),
        limit_bytes=usage.storage_limit_bytes(user),
        plan=user.plan,
    )


@router.get("/activity", response_model=list[ActivityItem])
async def my_activity(user: CurrentUser, session: SessionDep) -> list[ActivityItem]:
    """The latest things that happened to the person's videos: exports and new projects."""
    exported = (
        await session.execute(
            select(Project.id, Project.title, RenderJob.completed_at)
            .join(RenderJob, RenderJob.project_id == Project.id)
            .where(
                Project.owner_id == user.id,
                Project.deleted_at.is_(None),
                RenderJob.status == "completed",
                RenderJob.completed_at.is_not(None),
            )
            .order_by(RenderJob.completed_at.desc())
            .limit(10)
        )
    ).all()
    created = (
        await session.execute(
            select(Project.id, Project.title, Project.created_at)
            .where(Project.owner_id == user.id, Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .limit(10)
        )
    ).all()
    items = [ActivityItem(kind="exported", project_id=i, title=t, at=at) for i, t, at in exported]
    items += [ActivityItem(kind="created", project_id=i, title=t, at=at) for i, t, at in created]
    return sorted(items, key=lambda item: item.at, reverse=True)[:10]


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(payload: AccountDelete, user: CurrentUser, session: SessionDep) -> None:
    """Deletes the account and, through the cascade, every project in it."""
    if not verify_password(payload.password, user.hashed_password):
        raise AuthenticationError("That password is not right.", code="WRONG_PASSWORD")
    log.info("account_deleted", user_id=str(user.id), by="self")
    await session.delete(user)
    await session.commit()
