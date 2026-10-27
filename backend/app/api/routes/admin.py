"""Administration: the admin panel's control over people, and the telemetry service's
email lookup. Admins only; every change is written to the log (and so to telemetry) with
who did it and to whom.

The guards that matter: an admin cannot disable, demote or delete themselves, and the last
active admin can never be removed, so the panel cannot lock everyone out."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select

from app.api.dependencies import AdminUser, SessionDep
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.project import Project
from app.models.user import User
from app.schemas.account import (
    AdminStats,
    AdminUserDetail,
    AdminUserRow,
    AdminUserUpdate,
    BulkDelete,
    BulkDeleteResult,
    RecentProject,
)
from app.schemas.common import Page
from app.services import usage

router = APIRouter(prefix="/admin", tags=["admin"])
log = get_logger(__name__)

MAX_LOOKUP = 200


@router.get("/users/lookup")
async def lookup_users(
    _: AdminUser,
    session: SessionDep,
    ids: Annotated[str, Query(description="Comma-separated user ids")] = "",
) -> dict[str, str]:
    """{user_id: email} for the ids that exist; malformed or unknown ids are skipped.
    The telemetry service uses this to show emails next to user ids."""
    wanted: list[uuid.UUID] = []
    for part in ids.split(",")[:MAX_LOOKUP]:
        try:
            wanted.append(uuid.UUID(part.strip()))
        except ValueError:
            continue
    if not wanted:
        return {}
    rows = await session.execute(select(User.id, User.email).where(User.id.in_(wanted)))
    return {str(user_id): email for user_id, email in rows.all()}


@router.get("/stats", response_model=AdminStats)
async def stats(_: AdminUser, session: SessionDep) -> AdminStats:
    week = datetime.now(UTC) - timedelta(days=7)
    row = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(User.is_active),
                func.count().filter(User.is_admin),
                func.count().filter(User.created_at >= week),
            ).select_from(User)
        )
    ).one()
    projects = (await session.execute(select(func.count()).select_from(Project))).scalar_one()
    return AdminStats(
        users=int(row[0]),
        active=int(row[1]),
        admins=int(row[2]),
        new_7d=int(row[3]),
        projects=int(projects),
    )


async def _row(session: SessionDep, user: User) -> AdminUserRow:
    count = (
        await session.execute(
            select(func.count()).select_from(Project).where(Project.owner_id == user.id)
        )
    ).scalar_one()
    row = AdminUserRow.model_validate(user)
    row.project_count = int(count)
    row.used = await usage.current(user.id)
    return row


@router.get("/users", response_model=Page[AdminUserRow])
async def list_users(
    _: AdminUser,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    status_filter: Annotated[
        str, Query(alias="status", pattern="^(all|active|disabled|admin)$")
    ] = "all",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AdminUserRow]:
    where = []
    if q:
        like = f"%{q.strip().replace('%', '').replace('_', '')}%"
        where.append(or_(User.email.ilike(like), User.full_name.ilike(like)))
    if status_filter == "active":
        where.append(User.is_active)
    elif status_filter == "disabled":
        where.append(User.is_active.is_(False))
    elif status_filter == "admin":
        where.append(User.is_admin)
    total = (
        await session.execute(select(func.count()).select_from(User).where(*where))
    ).scalar_one()
    users = (
        (
            await session.execute(
                select(User)
                .where(*where)
                .order_by(User.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    # One project count per person in a single query, not one query each.
    counts = dict(
        (
            await session.execute(
                select(Project.owner_id, func.count())
                .where(Project.owner_id.in_([u.id for u in users]))
                .group_by(Project.owner_id)
            )
        ).all()
    )
    items = []
    for user in users:
        row = AdminUserRow.model_validate(user)
        row.project_count = int(counts.get(user.id, 0))
        row.used = await usage.current(user.id)
        items.append(row)
    return Page[AdminUserRow](items=items, total=int(total), limit=limit, offset=offset)


async def _get(session: SessionDep, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("No such user.", code="USER_NOT_FOUND")
    return user


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def user_detail(user_id: uuid.UUID, _: AdminUser, session: SessionDep) -> AdminUserDetail:
    user = await _get(session, user_id)
    recent = (
        (
            await session.execute(
                select(Project)
                .where(Project.owner_id == user.id)
                .order_by(Project.created_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    return AdminUserDetail(
        user=await _row(session, user),
        recent_projects=[
            RecentProject(id=p.id, title=p.title, status=str(p.status), created_at=p.created_at)
            for p in recent
        ],
    )


async def _other_active_admins(session: SessionDep, user_id: uuid.UUID) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_admin, User.is_active, User.id != user_id)
            )
        ).scalar_one()
    )


@router.patch("/users/{user_id}", response_model=AdminUserRow)
async def update_user(
    user_id: uuid.UUID, payload: AdminUserUpdate, admin: AdminUser, session: SessionDep
) -> AdminUserRow:
    user = await _get(session, user_id)
    sent = payload.model_fields_set
    losing_admin = ("is_active" in sent and payload.is_active is False) or (
        "is_admin" in sent and payload.is_admin is False
    )
    if losing_admin and user.id == admin.id:
        raise ConflictError(
            "You cannot disable or demote your own account.", code="CANNOT_CHANGE_SELF"
        )
    if losing_admin and user.is_admin and not await _other_active_admins(session, user.id):
        raise ConflictError("That would leave no active administrator.", code="LAST_ADMIN")

    changes: dict[str, object] = {}
    for field in (
        "full_name",
        "is_active",
        "is_admin",
        "plan",
        "limit_ai_calls",
        "limit_tokens",
        "limit_exports",
        "limit_storage_mb",
    ):
        if field in sent:
            value = getattr(payload, field)
            if getattr(user, field) != value:
                changes[field] = value
                setattr(user, field, value)
    await session.commit()
    log.info(
        "admin_user_updated",
        admin_id=str(admin.id),
        target_user_id=str(user.id),
        changes=changes,
    )
    return await _row(session, user)


@router.post("/users/{user_id}/reset-usage", status_code=status.HTTP_204_NO_CONTENT)
async def reset_usage(user_id: uuid.UUID, admin: AdminUser, session: SessionDep) -> None:
    """Zeroes this month's counters, e.g. after a support case."""
    user = await _get(session, user_id)
    await usage.reset(user.id)
    log.info("admin_usage_reset", admin_id=str(admin.id), target_user_id=str(user.id))


@router.post("/users/bulk-delete", response_model=BulkDeleteResult)
async def bulk_delete_users(
    payload: BulkDelete, admin: AdminUser, session: SessionDep
) -> BulkDeleteResult:
    """Deletes many accounts (and their projects) at once. Never yourself, and never so
    many administrators that none would be left; those are reported as skipped."""
    ids = set(payload.ids)
    remaining_admins = int(
        (
            await session.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_admin, User.is_active, User.id.not_in(ids))
            )
        ).scalar_one()
    )
    targets = (await session.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    skipped: list[dict[str, str]] = []
    deleted = 0
    for user in targets:
        if user.id == admin.id:
            skipped.append({"id": str(user.id), "reason": "That is your own account."})
        elif user.is_admin and remaining_admins == 0:
            skipped.append({"id": str(user.id), "reason": "That would leave no administrator."})
        else:
            await session.delete(user)
            deleted += 1
    await session.commit()
    log.info(
        "admin_users_bulk_deleted", admin_id=str(admin.id), deleted=deleted, skipped=len(skipped)
    )
    return BulkDeleteResult(deleted=deleted, skipped=skipped)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, admin: AdminUser, session: SessionDep) -> None:
    user = await _get(session, user_id)
    if user.id == admin.id:
        raise ConflictError("You cannot delete your own account here.", code="CANNOT_CHANGE_SELF")
    if user.is_admin and not await _other_active_admins(session, user.id):
        raise ConflictError("That would leave no active administrator.", code="LAST_ADMIN")
    await session.delete(user)
    await session.commit()
    log.info("admin_user_deleted", admin_id=str(admin.id), target_user_id=str(user_id))
