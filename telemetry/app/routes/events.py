"""The admin panel's read API: everything that was recorded, and how to look at it.

Admin only (the backend decides who is an admin, see auth/backend.py). Every list takes
the same filters, so the explorer, its facet counts, the histogram and the overview
always describe the same set of events.
"""

import csv
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import queries
from app.database import get_db
from auth import backend
from auth.deps import AdminToken

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

MAX_PAGE = 500
EXPORT_LIMIT = 10_000


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, f"Not a valid time: {value}") from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def filters(
    range: Annotated[str, Query(pattern="^(15m|1h|6h|24h|7d|30d|90d)$")] = queries.DEFAULT_RANGE,
    since: str | None = None,
    until: str | None = None,
    source: Annotated[list[str], Query()] = [],
    event_type: Annotated[list[str], Query()] = [],
    name: Annotated[list[str], Query()] = [],
    level: Annotated[list[str], Query()] = [],
    outcome: Annotated[list[str], Query()] = [],
    platform: Annotated[list[str], Query()] = [],
    hide: Annotated[list[str], Query()] = [],
    user: Annotated[str | None, Query(max_length=64)] = None,
    anonymous: bool | None = None,
    session: Annotated[str | None, Query(max_length=64)] = None,
    request_id: Annotated[str | None, Query(max_length=64)] = None,
    path: Annotated[str | None, Query(max_length=200)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> queries.Filters:
    start, end = queries.window(range)
    # An explicit window wins over the preset.
    start = _parse_time(since) or start
    end = _parse_time(until) or end
    if start >= end:
        raise HTTPException(422, "since must be before until")
    return queries.Filters(
        since=start,
        until=end,
        sources=source,
        event_types=event_type,
        names=name,
        levels=level,
        outcomes=outcome,
        platforms=platform,
        hide_names=hide,
        user_id=user,
        anonymous=anonymous,
        session_id=session,
        request_id=request_id,
        path=path,
        q=q,
    )


Filter = Annotated[queries.Filters, Depends(filters)]
Db = Annotated[AsyncSession, Depends(get_db)]


async def _with_emails(token: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = [i["user_id"] for i in items if i.get("user_id")]
    names = await backend.emails(token, ids) if ids else {}
    for item in items:
        item["user_email"] = names.get(item.get("user_id") or "")
    return items


@router.get("/events")
async def list_events(
    token: AdminToken,
    db: Db,
    f: Filter,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 100,
    before: str | None = None,
    after_seq: Annotated[int | None, Query(ge=0)] = None,
    include_total: bool = False,
):
    """Events, newest first. `before` (a cursor from a previous page) pages into the
    past; `after_seq` returns only what has ARRIVED since, which is the live tail."""
    cursor = queries.Cursor.decode(before)
    rows = await queries.search(db, f, limit=limit + 1, before=cursor, after_seq=after_seq)
    more = len(rows) > limit
    rows = rows[:limit]
    items = await _with_emails(token, [queries.to_dict(e) for e in rows])
    return {
        "events": items,
        "next_before": queries.Cursor(rows[-1].created_at, rows[-1].seq).encode()
        if more and rows
        else None,
        "latest_seq": await queries.latest_seq(db),
        "total": await queries.count(db, f) if include_total else None,
    }


@router.get("/events/facets")
async def event_facets(_: AdminToken, db: Db, f: Filter):
    return await queries.facets(db, f)


@router.get("/events/histogram")
async def event_histogram(_: AdminToken, db: Db, f: Filter):
    return await queries.histogram(db, f)


@router.get("/events/export")
async def export_events(
    _: AdminToken, db: Db, f: Filter, format: str = Query("json", pattern="^(json|csv)$")
):
    """The current filter as a file, newest first, up to 10,000 events."""
    rows = await queries.search(db, f, limit=EXPORT_LIMIT)
    items = [queries.to_dict(e) for e in rows]
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    if format == "json":
        body = json.dumps(items, default=str, ensure_ascii=False, indent=1)
        return StreamingResponse(
            iter([body]),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="events-{stamp}.json"'},
        )
    columns = [
        "created_at", "source", "event_type", "level", "outcome", "name", "user_id",
        "session_id", "request_id", "path", "duration_ms", "model", "provider",
        "total_tokens", "cost_usd", "platform", "os", "browser", "properties",
    ]  # fmt: skip
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for item in items:
        writer.writerow(
            [
                json.dumps(item["properties"], ensure_ascii=False)
                if c == "properties"
                else ("" if item.get(c) is None else item.get(c))
                for c in columns
            ]
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="events-{stamp}.csv"'},
    )


@router.get("/events/{event_id}")
async def event_detail(event_id: uuid.UUID, token: AdminToken, db: Db):
    """One event, plus everything that shares its request: the browser's call and the
    server's handling of it, side by side."""
    event = await queries.get_event(db, event_id)
    if event is None:
        raise HTTPException(404, "Event not found")
    item = queries.to_dict(event)
    related: list[dict[str, Any]] = []
    if event.request_id:
        everything = queries.Filters(
            since=datetime(2000, 1, 1, tzinfo=UTC),
            until=datetime(2100, 1, 1, tzinfo=UTC),
            request_id=event.request_id,
        )
        related = [
            queries.to_dict(e)
            for e in await queries.search(db, everything, limit=50, ascending=True)
            if e.id != event.id
        ]
    await _with_emails(token, [item, *related])
    return {"event": item, "same_request": related}


@router.get("/sessions")
async def list_sessions(
    token: AdminToken, db: Db, f: Filter, limit: Annotated[int, Query(ge=1, le=500)] = 100
):
    items = await queries.sessions(db, f, limit)
    return {"sessions": await _with_emails(token, items)}


@router.get("/sessions/{session_id}/timeline")
async def session_timeline(session_id: str, token: AdminToken, db: Db):
    rows = await queries.session_events(db, session_id)
    if not rows:
        raise HTTPException(404, "No events for this session")
    items = await _with_emails(token, [queries.to_dict(e) for e in rows])
    user_id = next((e.user_id for e in rows if e.user_id), None)
    return {
        "session_id": session_id,
        "user_id": user_id,
        "user_email": items[0].get("user_email") if user_id else None,
        "first_seen": rows[0].created_at,
        "last_seen": rows[-1].created_at,
        "events": items,
    }


@router.get("/users")
async def list_users(
    token: AdminToken, db: Db, f: Filter, limit: Annotated[int, Query(ge=1, le=500)] = 100
):
    return {"users": await _with_emails(token, await queries.users(db, f, limit))}


@router.get("/users/{user_id}")
async def user_detail(user_id: str, token: AdminToken, db: Db, f: Filter):
    f.user_id = user_id
    summary = (await queries.users(db, f, 1)) or []
    if not summary:
        raise HTTPException(404, "No events for this user in this range")
    [user] = await _with_emails(token, summary)
    return {
        "user": user,
        "sessions": await queries.sessions(db, f, 50),
        "top_events": await queries.top_names(db, f, 15),
        "errors": [
            queries.to_dict(e)
            for e in await queries.search(
                db,
                queries.Filters(since=f.since, until=f.until, user_id=user_id, levels=["error"]),
                limit=20,
            )
        ],
    }


@router.get("/overview")
async def overview(_: AdminToken, db: Db, f: Filter):
    return {
        **await queries.overview(db, f),
        "histogram": await queries.histogram(db, f),
        "since": f.since,
        "until": f.until,
    }


@router.get("/llm")
async def llm_usage(token: AdminToken, db: Db, f: Filter):
    """AI usage: totals, over time, by model and by person, and the latest failures."""
    data = await queries.llm(db, f)
    names = (
        await backend.emails(token, [u["user_id"] for u in data["by_user"]])
        if data["by_user"]
        else {}
    )
    for u in data["by_user"]:
        u["user_email"] = names.get(u["user_id"])
    await _with_emails(token, data["recent_failures"])
    return data
