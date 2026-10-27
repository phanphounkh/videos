"""EventIn -> Event row: the one place an incoming event becomes a stored one."""

import time
from datetime import UTC, datetime

from app.client_info import classify_client
from app.models.event import Event
from app.schemas.event import EventIn

# A client clock can be wrong. An event dated in the future, or from long ago, would
# land in the wrong place in every timeline, so such timestamps are replaced by "now".
MAX_FUTURE_S = 300
MAX_AGE_S = 3 * 86_400


def event_time(ts: float | None, now: float | None = None) -> datetime:
    now = time.time() if now is None else now
    if ts is None or not (now - MAX_AGE_S <= ts <= now + MAX_FUTURE_S):
        ts = now
    return datetime.fromtimestamp(ts, UTC)


def to_row(event: EventIn, now: float | None = None) -> Event:
    data = event.model_dump(exclude={"user_agent", "ts"})
    client = classify_client(event.user_agent)
    data["properties"] = data["properties"] or {}
    # Only fill the client buckets from the User-Agent when the sender did not.
    return Event(created_at=event_time(event.ts, now), **data, **client)
