"""Avatar (on-screen host) request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class BuiltinAvatar(BaseModel):
    id: str
    name: str
    style: Literal["toon", "real"]
    gender: Literal["male", "female"]
    age: Literal["young", "adult", "old"]
    preview_url: str


class CustomAvatarResponse(BaseModel):
    id: str  # "custom:<uuid>"
    name: str
    mode: Literal["mouth", "subtle"]
    image_url: str | None


class AvatarPreferences(BaseModel):
    default: str | None = Field(default=None, max_length=64)
    auto: bool = True


class AvatarCatalogue(BaseModel):
    builtin: list[BuiltinAvatar]
    custom: list[CustomAvatarResponse]
    preferences: AvatarPreferences


class CustomAvatarUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    mode: Literal["mouth", "subtle"] | None = None
