"""Account and admin-management schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

Metric = dict[str, int | None]


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class AccountDelete(BaseModel):
    password: str = Field(min_length=1, max_length=72)


class UsageResponse(BaseModel):
    plan: str
    period: str
    used: dict[str, int]
    limits: Metric
    projects: int
    exports_ready: int


class StorageResponse(BaseModel):
    used_bytes: int
    limit_bytes: int
    plan: str


class ActivityItem(BaseModel):
    kind: str  # exported | created
    project_id: uuid.UUID
    title: str
    at: datetime


class AdminUserRow(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    plan: str
    limit_ai_calls: int | None
    limit_tokens: int | None
    limit_exports: int | None
    limit_storage_mb: int | None = None
    created_at: datetime
    last_login_at: datetime | None
    project_count: int = 0
    used: dict[str, int] = {}


class RecentProject(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    created_at: datetime


class AdminUserDetail(BaseModel):
    user: AdminUserRow
    recent_projects: list[RecentProject]


class AdminUserUpdate(BaseModel):
    """Only the fields sent are changed. A limit of null means unlimited, so "not sent"
    and "unlimited" are told apart by `model_fields_set`."""

    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_admin: bool | None = None
    plan: str | None = Field(default=None, min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    limit_ai_calls: int | None = Field(default=None, ge=0)
    limit_tokens: int | None = Field(default=None, ge=0)
    limit_exports: int | None = Field(default=None, ge=0)
    limit_storage_mb: int | None = Field(default=None, ge=0)


class AdminStats(BaseModel):
    users: int
    active: int
    admins: int
    new_7d: int
    projects: int


class BulkDelete(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class BulkDeleteResult(BaseModel):
    deleted: int
    skipped: list[dict[str, str]]
