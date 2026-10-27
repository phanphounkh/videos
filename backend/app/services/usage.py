"""Monthly usage per person: counted as it happens, checked before the next costly step.

Counters live in Redis (one hash per person per month, kept ~70 days) because they are
incremented on every AI call and read on every check; the durable record of what happened
is the telemetry service. A Redis outage never blocks anyone: counting fails quietly and
the check lets the request through (a limit is a business rule, not a safety guard).

Limits are on the user row, set by an admin; None means unlimited.
"""

import contextlib
import uuid
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import QuotaExceededError
from app.models.user import User

METRICS = ("ai_calls", "tokens", "exports")
LABELS = {"ai_calls": "AI generations", "tokens": "AI tokens", "exports": "exports"}
KEEP_SECONDS = 70 * 86_400


def period(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m")


def _key(user_id: uuid.UUID | str, month: str) -> str:
    return f"sorya:usage:{user_id}:{month}"


def _client() -> redis.Redis:
    return redis.Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


async def add(user_id: uuid.UUID | str | None, metric: str, amount: int = 1) -> None:
    """Counts `amount` more of `metric` for this month. Never raises."""
    if user_id is None or metric not in METRICS or amount <= 0:
        return
    client = _client()
    try:
        key = _key(user_id, period())
        pipe = client.pipeline(transaction=False)
        pipe.hincrby(key, metric, int(amount))
        pipe.expire(key, KEEP_SECONDS)
        await pipe.execute()
    except Exception:  # noqa: BLE001 - counting must never break the work being counted
        pass
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()


async def current(user_id: uuid.UUID | str, month: str | None = None) -> dict[str, int]:
    """This month's totals ({} entries are zero). Never raises."""
    client = _client()
    try:
        raw = await client.hgetall(_key(user_id, month or period()))
    except Exception:  # noqa: BLE001
        raw = {}
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()
    return {m: int(raw.get(m, 0)) for m in METRICS}


async def reset(user_id: uuid.UUID | str) -> None:
    client = _client()
    try:
        await client.delete(_key(user_id, period()))
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()


# Default storage by plan, in MB; an admin can override it per person (limit_storage_mb).
PLAN_STORAGE_MB = {"free": 2_048, "pro": 20_480, "team": 102_400}
DEFAULT_STORAGE_MB = 2_048


def storage_limit_bytes(user: User) -> int:
    megabytes = user.limit_storage_mb or PLAN_STORAGE_MB.get(user.plan, DEFAULT_STORAGE_MB)
    return megabytes * 1024 * 1024


async def storage_used_bytes(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Everything the person has stored: uploads, generated media and finished renders.
    Trashed projects still count until they are deleted for good."""
    from sqlalchemy import func, select

    from app.models.asset import Asset
    from app.models.project import Project

    total = (
        await session.execute(
            select(func.coalesce(func.sum(Asset.size_bytes), 0))
            .select_from(Asset)
            .join(Project, Project.id == Asset.project_id)
            .where(Project.owner_id == user_id)
        )
    ).scalar_one()
    return int(total)


def limits_of(user: User) -> dict[str, int | None]:
    return {
        "ai_calls": user.limit_ai_calls,
        "tokens": user.limit_tokens,
        "exports": user.limit_exports,
    }


async def ensure_within(session: AsyncSession, user_id: uuid.UUID, metric: str) -> None:
    """Raises QuotaExceededError when `metric` is already at or over the person's cap."""
    user = await session.get(User, user_id)
    if user is None:
        return
    limit = limits_of(user)[metric]
    if limit is None:
        return
    used = (await current(user_id))[metric]
    if used >= limit:
        raise QuotaExceededError(
            f"You have used all {limit:,} {LABELS[metric]} on the {user.plan} plan this month.",
            details={"metric": metric, "used": used, "limit": limit, "plan": user.plan},
        )
