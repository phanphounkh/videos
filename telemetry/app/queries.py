"""The admin panel's questions, asked of the events table.

Everything is a filter or a group-by over one table. The same `Filters` drive the event
list, the facet counts, the histogram, the sessions and the overview, so what the panel
shows always agrees with itself.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import (
    Float,
    Text,
    and_,
    cast,
    func,
    literal,
    literal_column,
    or_,
    select,
    text,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

RANGES: dict[str, int] = {
    "15m": 900,
    "1h": 3_600,
    "6h": 21_600,
    "24h": 86_400,
    "7d": 604_800,
    "30d": 2_592_000,
    "90d": 7_776_000,
}
DEFAULT_RANGE = "24h"
# Candidate bucket sizes: each divides a day, so buckets line up with the epoch.
_BUCKETS = [1, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 21600, 43200, 86400]
_ORIGIN = "TIMESTAMPTZ '2000-01-01 00:00:00+00'"

FACET_FIELDS = ("source", "event_type", "level", "outcome", "platform")


@dataclass(slots=True)
class Filters:
    since: datetime
    until: datetime
    sources: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    levels: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    hide_names: list[str] = field(default_factory=list)
    user_id: str | None = None
    anonymous: bool | None = None
    session_id: str | None = None
    request_id: str | None = None
    path: str | None = None
    q: str | None = None


def window(range_name: str | None, now: datetime | None = None) -> tuple[datetime, datetime]:
    until = now or datetime.now(UTC)
    seconds = RANGES.get(range_name or DEFAULT_RANGE, RANGES[DEFAULT_RANGE])
    return until - timedelta(seconds=seconds), until


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def conditions(f: Filters, skip: str | None = None) -> list:
    """The WHERE clauses for `f`. `skip` leaves one facet's own filter out, so that
    facet's counts show the alternatives to the current choice."""
    c = [Event.created_at >= f.since, Event.created_at < f.until]
    if f.sources and skip != "source":
        c.append(Event.source.in_(f.sources))
    if f.event_types and skip != "event_type":
        c.append(Event.event_type.in_(f.event_types))
    if f.names and skip != "name":
        c.append(Event.name.in_(f.names))
    if f.levels and skip != "level":
        c.append(Event.level.in_(f.levels))
    if f.outcomes and skip != "outcome":
        c.append(Event.outcome.in_(f.outcomes))
    if f.platforms and skip != "platform":
        c.append(Event.platform.in_(f.platforms))
    if f.hide_names:
        c.append(Event.name.notin_(f.hide_names))
    if f.user_id:
        c.append(Event.user_id == f.user_id)
    if f.anonymous is True:
        c.append(Event.user_id.is_(None))
    elif f.anonymous is False:
        c.append(Event.user_id.is_not(None))
    if f.session_id:
        c.append(Event.session_id == f.session_id)
    if f.request_id:
        c.append(Event.request_id == f.request_id)
    if f.path:
        c.append(Event.path.ilike(f"%{_escape_like(f.path)}%", escape="\\"))
    if f.q:
        like = f"%{_escape_like(f.q)}%"
        c.append(
            or_(
                Event.name.ilike(like, escape="\\"),
                Event.path.ilike(like, escape="\\"),
                Event.user_id == f.q,
                Event.session_id == f.q,
                Event.request_id == f.q,
                cast(Event.properties, Text).ilike(like, escape="\\"),
            )
        )
    return c


# --------------------------------------------------------------------- the list
@dataclass(slots=True)
class Cursor:
    created_at: datetime
    seq: int

    def encode(self) -> str:
        return f"{self.created_at.isoformat()}|{self.seq}"

    @staticmethod
    def decode(raw: str | None) -> "Cursor | None":
        if not raw:
            return None
        try:
            stamp, _, seq = raw.rpartition("|")
            return Cursor(datetime.fromisoformat(stamp), int(seq))
        except (ValueError, TypeError):
            return None


async def search(
    db: AsyncSession,
    f: Filters,
    *,
    limit: int = 100,
    before: Cursor | None = None,
    after_seq: int | None = None,
    ascending: bool = False,
) -> list[Event]:
    """Newest first by default. `before` pages backwards through history; `after_seq`
    returns only events that ARRIVED after that point, for the live tail."""
    stmt = select(Event).where(*conditions(f))
    if before is not None:
        stmt = stmt.where(
            tuple_(Event.created_at, Event.seq) < tuple_(before.created_at, before.seq)
        )
    if after_seq is not None:
        stmt = stmt.where(Event.seq > after_seq)
    order = (
        (Event.created_at.asc(), Event.seq.asc())
        if ascending
        else (
            Event.created_at.desc(),
            Event.seq.desc(),
        )
    )
    return list((await db.execute(stmt.order_by(*order).limit(limit))).scalars().all())


async def get_event(db: AsyncSession, event_id) -> Event | None:
    return (await db.execute(select(Event).where(Event.id == event_id))).scalar_one_or_none()


async def count(db: AsyncSession, f: Filters) -> int:
    return int(
        (
            await db.execute(select(func.count()).select_from(Event).where(*conditions(f)))
        ).scalar_one()
    )


async def latest_seq(db: AsyncSession) -> int:
    return int((await db.execute(select(func.coalesce(func.max(Event.seq), 0)))).scalar_one())


# ------------------------------------------------------------------------ facets
async def facets(db: AsyncSession, f: Filters, name_limit: int = 40) -> dict[str, Any]:
    out: dict[str, Any] = {"total": await count(db, f)}
    for column in FACET_FIELDS:
        col = getattr(Event, column)
        rows = (
            await db.execute(
                select(col, func.count())
                .where(*conditions(f, skip=column), col.is_not(None))
                .group_by(col)
                .order_by(func.count().desc())
            )
        ).all()
        out[column] = [{"value": v, "count": int(n)} for v, n in rows]
    rows = (
        await db.execute(
            select(Event.name, func.count())
            .where(*conditions(f, skip="name"))
            .group_by(Event.name)
            .order_by(func.count().desc())
            .limit(name_limit)
        )
    ).all()
    out["name"] = [{"value": v, "count": int(n)} for v, n in rows]
    anonymous = (
        await db.execute(
            select(func.count()).select_from(Event).where(*conditions(f), Event.user_id.is_(None))
        )
    ).scalar_one()
    out["anonymous"] = int(anonymous)
    return out


# --------------------------------------------------------------------- histogram
def bucket_seconds(f: Filters) -> int:
    span = max(1.0, (f.until - f.since).total_seconds())
    return next((b for b in _BUCKETS if b >= span / 60), _BUCKETS[-1])


async def histogram(db: AsyncSession, f: Filters) -> dict[str, Any]:
    bucket = bucket_seconds(f)
    # Filters other than time apply too: build the same WHERE through the ORM and let
    # Postgres bin it, so the histogram and the list never disagree.
    stmt = (
        select(
            func.date_bin(
                func.make_interval(0, 0, 0, 0, 0, 0, literal(float(bucket))),
                Event.created_at,
                text(_ORIGIN),
            ).label("bucket"),
            func.count().label("total"),
            func.count().filter(Event.source == "frontend").label("frontend"),
            func.count().filter(Event.source == "backend").label("backend"),
            func.count().filter(Event.source == "worker").label("worker"),
            func.count().filter(Event.level == "error").label("errors"),
        )
        .where(*conditions(f))
        .group_by(text("1"))
        .order_by(text("1"))
    )
    rows = {r.bucket.astimezone(UTC): r for r in (await db.execute(stmt)).all()}

    buckets = []
    cursor = int(f.since.timestamp()) // bucket * bucket
    end = int(f.until.timestamp())
    while cursor <= end:
        stamp = datetime.fromtimestamp(cursor, UTC)
        row = rows.get(stamp)
        buckets.append(
            {
                "t": stamp,
                "total": int(row.total) if row else 0,
                "frontend": int(row.frontend) if row else 0,
                "backend": int(row.backend) if row else 0,
                "worker": int(row.worker) if row else 0,
                "errors": int(row.errors) if row else 0,
            }
        )
        cursor += bucket
    return {"bucket_seconds": bucket, "buckets": buckets}


# ---------------------------------------------------------------------- sessions
async def sessions(db: AsyncSession, f: Filters, limit: int = 100) -> list[dict[str, Any]]:
    """One row per session that had any event in the window: who, how long, how much."""
    stmt = (
        select(
            Event.session_id,
            func.max(Event.user_id).label("user_id"),
            func.min(Event.created_at).label("first_seen"),
            func.max(Event.created_at).label("last_seen"),
            func.count().label("events"),
            func.count().filter(Event.level == "error").label("errors"),
            func.count().filter(Event.name == "page_view").label("pages"),
            func.count().filter(Event.source == "backend").label("backend_events"),
            func.max(Event.platform).label("platform"),
            func.max(Event.browser).label("browser"),
        )
        .where(*conditions(f), Event.session_id.is_not(None))
        .group_by(Event.session_id)
        .order_by(func.max(Event.created_at).desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "session_id": r.session_id,
            "user_id": r.user_id,
            "first_seen": r.first_seen,
            "last_seen": r.last_seen,
            "duration_s": int((r.last_seen - r.first_seen).total_seconds()),
            "events": int(r.events),
            "errors": int(r.errors),
            "pages": int(r.pages),
            "backend_events": int(r.backend_events),
            "platform": r.platform,
            "browser": r.browser,
        }
        for r in rows
    ]


async def session_events(db: AsyncSession, session_id: str, limit: int = 5000) -> list[Event]:
    """Every event of one session, oldest first: the browser's clicks and the server work
    they caused, in one timeline."""
    stmt = (
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.created_at.asc(), Event.seq.asc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# ------------------------------------------------------------------------- users
async def users(db: AsyncSession, f: Filters, limit: int = 100) -> list[dict[str, Any]]:
    stmt = (
        select(
            Event.user_id,
            func.count().label("events"),
            func.count(func.distinct(Event.session_id)).label("sessions"),
            func.count().filter(Event.level == "error").label("errors"),
            func.min(Event.created_at).label("first_seen"),
            func.max(Event.created_at).label("last_seen"),
            func.max(Event.platform).label("platform"),
            func.max(Event.browser).label("browser"),
        )
        .where(*conditions(f), Event.user_id.is_not(None))
        .group_by(Event.user_id)
        .order_by(func.max(Event.created_at).desc())
        .limit(limit)
    )
    return [
        {
            "user_id": r.user_id,
            "events": int(r.events),
            "sessions": int(r.sessions),
            "errors": int(r.errors),
            "first_seen": r.first_seen,
            "last_seen": r.last_seen,
            "platform": r.platform,
            "browser": r.browser,
        }
        for r in (await db.execute(stmt)).all()
    ]


async def top_names(db: AsyncSession, f: Filters, limit: int = 15) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Event.name, func.count())
            .where(*conditions(f))
            .group_by(Event.name)
            .order_by(func.count().desc())
            .limit(limit)
        )
    ).all()
    return [{"name": n, "count": int(c)} for n, c in rows]


# ---------------------------------------------------------------------- overview
async def overview(db: AsyncSession, f: Filters) -> dict[str, Any]:
    base = conditions(f)
    totals = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(Event.level == "error"),
                func.count().filter(Event.level == "warning"),
                func.count(func.distinct(Event.user_id)),
                func.count(func.distinct(Event.session_id)),
                func.count().filter(Event.user_id.is_(None)),
            ).where(*base)
        )
    ).one()
    by_source = {
        s: int(n)
        for s, n in (
            await db.execute(select(Event.source, func.count()).where(*base).group_by(Event.source))
        ).all()
    }

    api_where = and_(Event.source == "backend", Event.name == "api_request")
    api = (
        await db.execute(
            select(
                func.count().filter(api_where),
                func.count().filter(api_where, Event.outcome == "error"),
                func.percentile_cont(0.5).within_group(Event.duration_ms).filter(api_where),
                func.percentile_cont(0.95).within_group(Event.duration_ms).filter(api_where),
            ).where(*base)
        )
    ).one()

    llm_where = Event.event_type == "llm_usage"
    llm = (
        await db.execute(
            select(
                func.count().filter(llm_where),
                func.count().filter(llm_where, Event.outcome == "error"),
                func.coalesce(func.sum(Event.total_tokens).filter(llm_where), 0),
                func.sum(Event.cost_usd).filter(llm_where),
                func.avg(Event.duration_ms).filter(llm_where),
            ).where(*base)
        )
    ).one()
    llm_models = (
        await db.execute(
            select(
                Event.name,
                Event.provider,
                Event.model,
                func.count(),
                func.coalesce(func.sum(Event.total_tokens), 0),
                func.sum(Event.cost_usd),
                func.avg(Event.duration_ms),
                func.count().filter(Event.outcome == "error"),
            )
            .where(*base, llm_where)
            .group_by(Event.name, Event.provider, Event.model)
            .order_by(func.count().desc())
            .limit(20)
        )
    ).all()

    render_where = and_(Event.source == "worker", Event.name == "render_job")
    render = (
        await db.execute(
            select(
                func.count().filter(render_where),
                func.count().filter(render_where, Event.outcome == "error"),
                func.avg(Event.duration_ms).filter(render_where, Event.outcome == "ok"),
                func.percentile_cont(0.95)
                .within_group(Event.duration_ms)
                .filter(render_where, Event.outcome == "ok"),
            ).where(*base)
        )
    ).one()

    # Literal JSON paths, not bound parameters: Postgres can only match a GROUP BY
    # expression to the SELECT list when they are textually identical.
    metric = literal_column("(events.properties ->> 'metric')")
    value = cast(literal_column("(events.properties ->> 'value')"), Float)
    vitals = (
        await db.execute(
            select(metric, func.count(), func.percentile_cont(0.75).within_group(value))
            .where(*base, Event.name == "web_vital", metric.is_not(None))
            .group_by(metric)
        )
    ).all()

    return {
        "totals": {
            "events": int(totals[0]),
            "errors": int(totals[1]),
            "warnings": int(totals[2]),
            "users": int(totals[3]),
            "sessions": int(totals[4]),
            "anonymous_events": int(totals[5]),
        },
        "by_source": by_source,
        "api": {
            "requests": int(api[0]),
            "errors": int(api[1]),
            "p50_ms": float(api[2]) if api[2] is not None else None,
            "p95_ms": float(api[3]) if api[3] is not None else None,
        },
        "llm": {
            "calls": int(llm[0]),
            "failures": int(llm[1]),
            "tokens": int(llm[2]),
            "cost_usd": float(llm[3]) if llm[3] is not None else None,
            "avg_ms": float(llm[4]) if llm[4] is not None else None,
            "by_model": [
                {
                    "call": r[0],
                    "provider": r[1],
                    "model": r[2],
                    "calls": int(r[3]),
                    "tokens": int(r[4]),
                    "cost_usd": float(r[5]) if r[5] is not None else None,
                    "avg_ms": float(r[6]) if r[6] is not None else None,
                    "failures": int(r[7]),
                }
                for r in llm_models
            ],
        },
        "renders": {
            "jobs": int(render[0]),
            "failed": int(render[1]),
            "avg_ms": float(render[2]) if render[2] is not None else None,
            "p95_ms": float(render[3]) if render[3] is not None else None,
        },
        "web_vitals": [
            {"metric": m, "samples": int(n), "p75": float(p) if p is not None else None}
            for m, n, p in vitals
        ],
        "top_events": await top_names(db, f),
    }


async def llm(db: AsyncSession, f: Filters) -> dict[str, Any]:
    """Everything about AI usage in the window: totals, a time series, and who and what
    used it. Other filters (user, name, ...) narrow it like everywhere else."""
    where = [*conditions(f), Event.event_type == "llm_usage"]
    t = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(Event.outcome == "error"),
                func.coalesce(func.sum(Event.total_tokens), 0),
                func.coalesce(func.sum(Event.prompt_tokens), 0),
                func.coalesce(func.sum(Event.completion_tokens), 0),
                func.sum(Event.cost_usd),
                func.avg(Event.duration_ms),
                func.percentile_cont(0.95).within_group(Event.duration_ms),
                func.count(func.distinct(Event.user_id)),
            ).where(*where)
        )
    ).one()

    bucket = bucket_seconds(f)
    stmt = (
        select(
            func.date_bin(
                func.make_interval(0, 0, 0, 0, 0, 0, literal(float(bucket))),
                Event.created_at,
                text(_ORIGIN),
            ).label("bucket"),
            func.count().label("calls"),
            func.count().filter(Event.outcome == "error").label("failures"),
            func.coalesce(func.sum(Event.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(Event.cost_usd), 0).label("cost"),
        )
        .where(*where)
        .group_by(text("1"))
        .order_by(text("1"))
    )
    rows = {r.bucket.astimezone(UTC): r for r in (await db.execute(stmt)).all()}
    series = []
    cursor = int(f.since.timestamp()) // bucket * bucket
    while cursor <= int(f.until.timestamp()):
        stamp = datetime.fromtimestamp(cursor, UTC)
        r = rows.get(stamp)
        series.append(
            {
                "t": stamp,
                "calls": int(r.calls) if r else 0,
                "failures": int(r.failures) if r else 0,
                "tokens": int(r.tokens) if r else 0,
                "cost_usd": float(r.cost) if r else 0.0,
            }
        )
        cursor += bucket

    by_model = (
        await db.execute(
            select(
                Event.name,
                Event.provider,
                Event.model,
                func.count(),
                func.count().filter(Event.outcome == "error"),
                func.coalesce(func.sum(Event.total_tokens), 0),
                func.sum(Event.cost_usd),
                func.avg(Event.duration_ms),
                func.percentile_cont(0.95).within_group(Event.duration_ms),
            )
            .where(*where)
            .group_by(Event.name, Event.provider, Event.model)
            .order_by(func.count().desc())
            .limit(30)
        )
    ).all()
    by_user = (
        await db.execute(
            select(
                Event.user_id,
                func.count(),
                func.count().filter(Event.outcome == "error"),
                func.coalesce(func.sum(Event.total_tokens), 0),
                func.sum(Event.cost_usd),
            )
            .where(*where, Event.user_id.is_not(None))
            .group_by(Event.user_id)
            .order_by(func.count().desc())
            .limit(25)
        )
    ).all()
    failures = (
        (
            await db.execute(
                select(Event)
                .where(*where, Event.outcome == "error")
                .order_by(Event.created_at.desc(), Event.seq.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    num = lambda v: float(v) if v is not None else None  # noqa: E731
    return {
        "totals": {
            "calls": int(t[0]),
            "failures": int(t[1]),
            "tokens": int(t[2]),
            "prompt_tokens": int(t[3]),
            "completion_tokens": int(t[4]),
            "cost_usd": num(t[5]),
            "avg_ms": num(t[6]),
            "p95_ms": num(t[7]),
            "users": int(t[8]),
        },
        "bucket_seconds": bucket,
        "series": series,
        "by_model": [
            {
                "call": r[0],
                "provider": r[1],
                "model": r[2],
                "calls": int(r[3]),
                "failures": int(r[4]),
                "tokens": int(r[5]),
                "cost_usd": num(r[6]),
                "avg_ms": num(r[7]),
                "p95_ms": num(r[8]),
            }
            for r in by_model
        ],
        "by_user": [
            {
                "user_id": r[0],
                "calls": int(r[1]),
                "failures": int(r[2]),
                "tokens": int(r[3]),
                "cost_usd": num(r[4]),
            }
            for r in by_user
        ],
        "recent_failures": [to_dict(e) for e in failures],
    }


def to_dict(e: Event) -> dict[str, Any]:
    """An event as the API returns it."""
    return {
        "id": str(e.id),
        "seq": e.seq,
        "created_at": e.created_at,
        "event_type": e.event_type,
        "name": e.name,
        "source": e.source,
        "level": e.level,
        "outcome": e.outcome,
        "user_id": e.user_id,
        "session_id": e.session_id,
        "request_id": e.request_id,
        "path": e.path,
        "duration_ms": e.duration_ms,
        "model": e.model,
        "provider": e.provider,
        "prompt_tokens": e.prompt_tokens,
        "completion_tokens": e.completion_tokens,
        "total_tokens": e.total_tokens,
        "finish_reason": e.finish_reason,
        "cost_usd": e.cost_usd,
        "properties": e.properties or {},
        "platform": e.platform,
        "os": e.os,
        "browser": e.browser,
    }
