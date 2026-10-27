"""Path B: browser events.

The browser posts here through the web app's same-origin proxy. Nothing about the
sender is trusted:

  - identity comes from the verified token, never from the body; with no valid token
    the events are still accepted, anonymously (the login page, errors before sign-in),
    under a stricter per-IP limit;
  - the source is always "frontend", so a browser cannot pass itself off as the server;
  - every item is checked on its own, so one bad item never costs the rest of its batch;
  - names, sizes and nesting are bounded, and emails and tokens are scrubbed.
"""

import asyncio
import json
import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import ratelimit
from app.client_info import classify_client
from app.config import get_settings
from app.database import get_db
from app.models.event import Event
from app.sanitize import TooDeep, clean, parse_json
from app.schemas.event import LEVELS
from app.store import event_time
from auth.deps import optional_user
from auth.tokens import Principal

log = logging.getLogger("telemetry.ingest")
router = APIRouter(prefix="/ingest", tags=["ingest"])
settings = get_settings()

# Any name of this shape: the vocabulary is the app's, not ours. Bounded so a bug cannot
# create unbounded distinct names, and lower-case so "Click" and "click" are one thing.
NAME = re.compile(r"^[a-z][a-z0-9_.:-]{0,79}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
MAX_PROPERTIES_BYTES = 8 * 1024
MAX_STRING_CHARS = 2000
MAX_DEPTH = 8
MAX_PATH = 300


def _bad(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


async def _read_json(request: Request, max_bytes: int):
    """The body, with a hard size cap enforced while streaming (Content-Length may lie)."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"Body too large (max {max_bytes} bytes)"
        )
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE, f"Body too large (max {max_bytes} bytes)"
            )
        chunks.append(chunk)
    try:
        # Parsed off the event loop: a megabyte of nested JSON would stall everyone.
        return await asyncio.to_thread(parse_json, b"".join(chunks))
    except (ValueError, RecursionError):
        raise _bad("Body is not valid JSON") from None


def _session_id(value) -> str:
    if not isinstance(value, str):
        raise _bad("session_id must be a UUID string")
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise _bad("session_id must be a UUID string") from None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    return first or (request.client.host if request.client else "unknown")


def accept_item(item, now: float | None = None) -> dict | None:
    """The event's columns for a valid item, or None to drop it."""
    if not isinstance(item, dict):
        return None
    name = item.get("name")
    if not isinstance(name, str) or not NAME.match(name):
        return None

    ts = item.get("ts")  # milliseconds, from Date.now()
    if ts is not None and (
        isinstance(ts, bool) or not isinstance(ts, int | float) or not 0 <= ts < 2**53
    ):
        return None

    level = item.get("level", "info")
    if level not in LEVELS:
        return None

    duration = item.get("duration_ms")
    if duration is not None:
        if isinstance(duration, bool) or not isinstance(duration, int | float):
            return None
        if not 0 <= duration <= 3_600_000:
            return None
        duration = int(duration)

    request_id = item.get("request_id")
    if request_id is not None and (
        not isinstance(request_id, str) or not REQUEST_ID.match(request_id)
    ):
        return None

    path = item.get("path")
    if path is not None:
        if not isinstance(path, str):
            return None
        path = clean(path, max_chars=MAX_PATH)

    props = item.get("properties", {})
    if not isinstance(props, dict):
        return None
    try:
        props = clean(props, max_chars=MAX_STRING_CHARS, max_depth=MAX_DEPTH)
    except TooDeep:
        return None
    if (
        len(json.dumps(props, ensure_ascii=False, separators=(",", ":")).encode())
        > MAX_PROPERTIES_BYTES
    ):
        return None

    outcome = "error" if level == "error" else None
    return {
        "name": name,
        "level": level,
        "outcome": outcome,
        "duration_ms": duration,
        "request_id": request_id,
        "path": path,
        "properties": props,
        "created_at": event_time(ts / 1000 if ts is not None else None, now),
    }


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(
    request: Request,
    user: Principal | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
):
    if user is not None:
        await ratelimit.enforce("events", user.id, settings.ingest_rate_limit_max)
    else:
        await ratelimit.enforce("anon", _client_ip(request), settings.ingest_anon_rate_limit_max)

    body = await _read_json(request, settings.ingest_max_body_bytes)
    if not isinstance(body, dict):
        raise _bad("Body must be a JSON object")
    session_id = _session_id(body.get("session_id"))
    items = body.get("events")
    limit = settings.ingest_max_events_per_batch
    if not isinstance(items, list) or not 1 <= len(items) <= limit:
        raise _bad(f"events must be a list of 1..{limit} items")

    client = classify_client(request.headers.get("user-agent"))
    # Sanitising walks every value in pure Python: kept off the event loop.
    accepted = await asyncio.to_thread(lambda: [accept_item(item) for item in items])
    rows = [
        Event(
            event_type="product",
            source="frontend",
            user_id=user.id if user else None,
            session_id=session_id,
            **columns,
            **client,
        )
        for columns in accepted
        if columns is not None
    ]
    if rows:
        db.add_all(rows)
        await db.commit()
    rejected = len(items) - len(rows)
    if rejected:
        log.debug("ingest: dropped %d of %d browser events", rejected, len(items))
    return {"accepted": len(rows), "rejected": rejected}
