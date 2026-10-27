"""Selectable on-screen hosts ("avatars").

Twelve built-in hosts (cartoon and semi-realistic, three ages, two genders) plus the
photos each person uploads. Everything refers to a host by one string id: a built-in id
such as "toon-f-young", or "custom:<uuid>" for an upload.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.custom_avatar import CustomAvatar
from app.models.user import User
from app.services.storage.urls import renderer_url

CUSTOM_PREFIX = "custom:"
MAX_CUSTOM_AVATARS = 12


@dataclass(frozen=True)
class BuiltinAvatarInfo:
    id: str
    name: str
    style: Literal["toon", "real"]
    gender: Literal["male", "female"]
    age: Literal["young", "adult", "old"]

    @property
    def preview_url(self) -> str:
        return f"/avatars/{self.id}.png"


_NAMES = {
    "toon-m-young": "Dara",
    "toon-f-young": "Sophea",
    "toon-m-adult": "Vuthy",
    "toon-f-adult": "Chenda",
    "toon-m-old": "Ta Sok",
    "toon-f-old": "Yeay Sarun",
    "real-m-young": "Rithy",
    "real-f-young": "Maly",
    "real-m-adult": "Samnang",
    "real-f-adult": "Bopha",
    "real-m-old": "Lok Sen",
    "real-f-old": "Daun Pen",
}


def _build() -> dict[str, BuiltinAvatarInfo]:
    out: dict[str, BuiltinAvatarInfo] = {}
    for avatar_id, name in _NAMES.items():
        style, g, age = avatar_id.split("-")
        out[avatar_id] = BuiltinAvatarInfo(
            id=avatar_id,
            name=name,
            style=style,  # type: ignore[arg-type]
            gender="male" if g == "m" else "female",
            age=age,  # type: ignore[arg-type]
        )
    return out


BUILTIN_AVATARS: dict[str, BuiltinAvatarInfo] = _build()

# Purposes that wear the cartoon hosts; every other purpose gets the realistic ones.
CARTOON_PURPOSES = {"story", "social_post", "creator"}
PURPOSE_DEFAULTS = {
    "story": "toon-m-young",
    "social_post": "toon-f-young",
    "creator": "toon-m-adult",
    "product_demo": "real-f-adult",
    "explainer": "real-m-adult",
}
FALLBACK_AVATAR = "toon-m-young"


def custom_uuid(avatar_id: str) -> uuid.UUID | None:
    """The uuid inside a "custom:<uuid>" id, or None if it is not one."""
    if not avatar_id.startswith(CUSTOM_PREFIX):
        return None
    try:
        return uuid.UUID(avatar_id[len(CUSTOM_PREFIX) :])
    except ValueError:
        return None


def resolve_avatar(project_avatar: str | None, user: User | None, purpose: str) -> str:
    """The host a video actually uses: the project's own choice, else the person's
    favourite (restyled to suit the video when 'auto' is on), else the purpose default."""
    if project_avatar:
        return project_avatar
    favourite = user.avatar_default if user is not None else None
    if favourite:
        if favourite.startswith(CUSTOM_PREFIX):
            return favourite
        info = BUILTIN_AVATARS.get(favourite)
        if info is not None:
            if not user.avatar_auto:  # type: ignore[union-attr]
                return favourite
            style = "toon" if purpose in CARTOON_PURPOSES else "real"
            return f"{style}-{favourite.split('-', 1)[1]}"
    return PURPOSE_DEFAULTS.get(purpose, FALLBACK_AVATAR)


async def validate_choice(session: AsyncSession, owner_id: uuid.UUID, avatar_id: str) -> None:
    """Raises 422 INVALID_AVATAR unless the id is a built-in one or the person's own upload."""
    if avatar_id in BUILTIN_AVATARS:
        return
    ident = custom_uuid(avatar_id)
    if ident is not None:
        row = await session.get(CustomAvatar, ident)
        if row is not None and row.owner_id == owner_id:
            return
    raise ValidationError("That avatar does not exist.", code="INVALID_AVATAR")


def builtin_spec(avatar_id: str) -> dict[str, Any]:
    return {"kind": "builtin", "id": avatar_id, "imageUrl": None, "mode": "mouth"}


def photo_spec(row: CustomAvatar) -> dict[str, Any]:
    return {
        "kind": "photo",
        "id": row.ref,
        "imageUrl": renderer_url(row.storage_key),
        "mode": row.mode,
    }


async def avatar_spec(session: AsyncSession, project: Any) -> dict[str, Any]:
    """The `avatar` object of the renderer payload for a project (database lookup for
    uploaded photos). A photo that has vanished falls back to the purpose default."""
    resolved = resolve_avatar(project.avatar, project.owner, project.purpose)
    ident = custom_uuid(resolved)
    if ident is not None:
        row = (
            await session.execute(
                select(CustomAvatar).where(
                    CustomAvatar.id == ident, CustomAvatar.owner_id == project.owner_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            return photo_spec(row)
        return builtin_spec(resolve_avatar(None, None, project.purpose))
    return builtin_spec(resolved)


def sync_spec(project: Any, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    """`spec` from `avatar_spec` when the caller has it; otherwise a built-in-only answer
    (an uploaded photo needs a database lookup, so without `spec` it falls back)."""
    if spec is not None:
        return spec
    resolved = resolve_avatar(project.avatar, project.owner, project.purpose)
    if custom_uuid(resolved) is not None:
        resolved = resolve_avatar(None, None, project.purpose)
    return builtin_spec(resolved)
