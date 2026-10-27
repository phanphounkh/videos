"""On-screen hosts: the built-in catalogue and the person's own photo avatars."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import func, select, update

from app.api.dependencies import CurrentUser, SessionDep
from app.api.routes.account import _square_jpeg
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.custom_avatar import CustomAvatar
from app.models.project import Project
from app.schemas.avatar import (
    AvatarCatalogue,
    AvatarPreferences,
    BuiltinAvatar,
    CustomAvatarResponse,
    CustomAvatarUpdate,
)
from app.services.avatars import BUILTIN_AVATARS, MAX_CUSTOM_AVATARS
from app.services.storage import get_storage, public_url

router = APIRouter(prefix="/avatars", tags=["avatars"])
log = get_logger(__name__)

PHOTO_SIZE = 512
PHOTO_MAX_BYTES = 8 * 1024 * 1024


def _item(row: CustomAvatar) -> CustomAvatarResponse:
    return CustomAvatarResponse(
        id=row.ref,
        name=row.name,
        mode=row.mode,  # type: ignore[arg-type]
        image_url=public_url(row.storage_key),
    )


async def _owned(session: SessionDep, avatar_id: uuid.UUID, owner_id: uuid.UUID) -> CustomAvatar:
    row = await session.get(CustomAvatar, avatar_id)
    if row is None or row.owner_id != owner_id:
        raise NotFoundError("Avatar was not found.", code="AVATAR_NOT_FOUND")
    return row


async def _delete_object(key: str) -> None:
    try:
        await get_storage().delete(key)
    except Exception as exc:  # noqa: BLE001 - an orphaned file is not worth failing for
        log.warning("avatar_photo_cleanup_failed", error=str(exc)[:200])


@router.get("", response_model=AvatarCatalogue)
async def list_avatars(user: CurrentUser, session: SessionDep) -> AvatarCatalogue:
    rows = (
        (
            await session.execute(
                select(CustomAvatar)
                .where(CustomAvatar.owner_id == user.id)
                .order_by(CustomAvatar.created_at, CustomAvatar.id)
            )
        )
        .scalars()
        .all()
    )
    return AvatarCatalogue(
        builtin=[
            BuiltinAvatar(
                id=a.id,
                name=a.name,
                style=a.style,
                gender=a.gender,
                age=a.age,
                preview_url=a.preview_url,
            )
            for a in BUILTIN_AVATARS.values()
        ],
        custom=[_item(r) for r in rows],
        preferences=AvatarPreferences(default=user.avatar_default, auto=user.avatar_auto),
    )


@router.post("", response_model=CustomAvatarResponse, status_code=status.HTTP_201_CREATED)
async def upload_avatar(
    file: Annotated[UploadFile, File()],
    user: CurrentUser,
    session: SessionDep,
    name: Annotated[str, Form(max_length=60)] = "My avatar",
    mode: Annotated[Literal["mouth", "subtle"], Form()] = "mouth",
) -> CustomAvatarResponse:
    count = (
        await session.execute(
            select(func.count()).select_from(CustomAvatar).where(CustomAvatar.owner_id == user.id)
        )
    ).scalar_one()
    if count >= MAX_CUSTOM_AVATARS:
        raise ConflictError(
            f"You can keep up to {MAX_CUSTOM_AVATARS} avatars. Delete one to add another.",
            code="AVATAR_LIMIT",
        )
    data = await file.read(PHOTO_MAX_BYTES + 1)
    if len(data) > PHOTO_MAX_BYTES:
        raise ValidationError("That picture is larger than 8 MB.", code="FILE_TOO_LARGE")
    if not data:
        raise ValidationError("The uploaded file is empty.", code="EMPTY_FILE")
    jpeg = _square_jpeg(data, PHOTO_SIZE)

    key = f"avatar-photos/{user.id}/{uuid.uuid4().hex}.jpg"
    await get_storage().put_bytes(key, jpeg, "image/jpeg")
    row = CustomAvatar(
        owner_id=user.id, name=name.strip() or "My avatar", storage_key=key, mode=mode
    )
    session.add(row)
    try:
        await session.commit()
    except Exception:
        await _delete_object(key)
        raise
    log.info("avatar_uploaded", user_id=str(user.id), avatar_id=str(row.id), bytes=len(jpeg))
    return _item(row)


@router.patch("/{avatar_id}", response_model=CustomAvatarResponse)
async def update_avatar(
    avatar_id: uuid.UUID, payload: CustomAvatarUpdate, user: CurrentUser, session: SessionDep
) -> CustomAvatarResponse:
    row = await _owned(session, avatar_id, user.id)
    if payload.name is not None:
        row.name = payload.name.strip() or row.name
    if payload.mode is not None:
        row.mode = payload.mode
    await session.commit()
    await session.refresh(row)
    return _item(row)


@router.delete("/{avatar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(avatar_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    row = await _owned(session, avatar_id, user.id)
    ref, key = row.ref, row.storage_key
    # Videos that used this photo go back to automatic; so does a favourite pointing at it.
    await session.execute(
        update(Project)
        .where(Project.owner_id == user.id, Project.avatar == ref)
        .values(avatar=None)
        .execution_options(synchronize_session="fetch")
    )
    if user.avatar_default == ref:
        user.avatar_default = None
    await session.delete(row)
    await session.commit()
    await _delete_object(key)
    log.info("avatar_deleted", user_id=str(user.id), avatar_id=str(avatar_id))
