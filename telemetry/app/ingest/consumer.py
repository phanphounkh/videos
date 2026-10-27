"""Path A: the backend and worker XADD events onto a Redis stream; this reads them.

Streams, not a plain list, so a crash mid-batch leaves the entries unacknowledged and
reclaimable instead of lost. Every entry is persisted in its own SAVEPOINT, so one row
the database refuses is dropped alone, never costing the rest of its batch.
"""

import asyncio
import logging

import redis.asyncio as redis
from sqlalchemy.exc import DBAPIError

from app.config import get_settings
from app.database import SessionLocal
from app.sanitize import clean, parse_json
from app.schemas.event import EventIn
from app.store import to_row

log = logging.getLogger("telemetry.consumer")
settings = get_settings()

_READ_COUNT = 100
_BLOCK_MS = 5000
_RETRY_S = 5

# What /health/checks reports. The consumer is a background task nobody awaits, so
# without this a consumer that died at startup looks exactly like one idling on an
# empty stream. Counters reset on restart; the row count in the database is cumulative.
STATUS: dict = {
    "state": "not_started",  # not_started | connecting | live | retrying
    "error": None,
    "persisted": 0,
    "dropped": 0,  # malformed: could not be parsed into an EventIn
    "rejected": 0,  # parsed, but the database refused the row
}


def client() -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        # XREADGROUP's own `block` must bound the wait; a client read timeout on top of
        # it would race it and trip on nearly every idle poll.
        socket_timeout=None,
    )


async def _ensure_group(r: redis.Redis) -> None:
    try:
        await r.xgroup_create(
            settings.telemetry_stream_key, settings.telemetry_consumer_group, id="0", mkstream=True
        )
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def parse_entry(entry_id: str, fields: dict) -> EventIn | None:
    """The entry's event, or None when malformed. Strings are cleaned first."""
    try:
        payload = parse_json(fields["payload"])
        if not isinstance(payload, dict):
            raise ValueError(f"payload is a JSON {type(payload).__name__}, not an object")
        return EventIn(**clean(payload, max_chars=2000))
    except (KeyError, ValueError, RecursionError, TypeError):
        log.exception("dropping malformed telemetry entry %s", entry_id)
        return None


def rejects_row(exc: DBAPIError) -> bool:
    """Whether the database refused this row's own values (data exception, integrity
    violation, size limit): those fail the same way on every redelivery. Anything else
    (connection lost, timeout) says nothing about the row, so the batch is retried."""
    sqlstate = getattr(exc.orig, "sqlstate", None) or ""
    return sqlstate[:2] in ("22", "23", "54")


async def persist(db, entry_id: str, event: EventIn) -> bool:
    try:
        async with db.begin_nested():
            db.add(to_row(event))
    except DBAPIError as exc:
        if not rejects_row(exc):
            raise
        log.exception("dropping entry %s (%s): the database refused it", entry_id, event.name)
        return False
    return True


async def process_batch(r: redis.Redis, entries: list[tuple[str, dict]]) -> None:
    """Persist every entry, then ack all of them, including ones that cannot ever
    succeed (malformed, refused): leaving a poison pill unacknowledged would stop all
    ingest behind it on every restart."""
    persisted = dropped = rejected = 0
    async with SessionLocal() as db:
        for entry_id, fields in entries:
            event = parse_entry(entry_id, fields)
            if event is None:
                dropped += 1
            elif await persist(db, entry_id, event):
                persisted += 1
            else:
                rejected += 1
        await db.commit()
    STATUS["persisted"] += persisted
    STATUS["dropped"] += dropped
    STATUS["rejected"] += rejected
    if dropped == len(entries):
        log.error(
            "ALL %d entries in this batch failed to parse: EventIn is probably out of sync "
            "with the backend's telemetry client",
            dropped,
        )
    await r.xack(
        settings.telemetry_stream_key,
        settings.telemetry_consumer_group,
        *[entry_id for entry_id, _ in entries],
    )


async def consume_forever() -> None:
    """Supervisor: any failure is recorded in STATUS and retried, never fatal."""
    while True:
        try:
            STATUS["state"] = "connecting"
            r = client()
            try:
                await _run(r)
            finally:
                await r.aclose()
        except asyncio.CancelledError:
            STATUS["state"] = "not_started"
            raise
        except Exception as exc:  # noqa: BLE001
            STATUS["state"] = "retrying"
            STATUS["error"] = f"{type(exc).__name__}: {exc}"[:200]
            log.exception("telemetry consumer failed, retrying in %ds", _RETRY_S)
            await asyncio.sleep(_RETRY_S)


async def _run(r: redis.Redis) -> None:
    key, group, name = (
        settings.telemetry_stream_key,
        settings.telemetry_consumer_group,
        settings.hostname,
    )
    await _ensure_group(r)

    # First reclaim this consumer's own delivered-but-unacknowledged entries from a
    # previous crash, then join the live stream.
    while True:
        resp = await r.xreadgroup(group, name, {key: "0"}, count=_READ_COUNT)
        entries = resp[0][1] if resp else []
        if not entries:
            break
        log.info("reclaiming %d pending entries from a previous run", len(entries))
        await process_batch(r, entries)

    log.info("consumer live on stream=%s group=%s consumer=%s", key, group, name)
    STATUS["state"] = "live"
    STATUS["error"] = None
    while True:
        try:
            resp = await r.xreadgroup(group, name, {key: ">"}, count=_READ_COUNT, block=_BLOCK_MS)
        except redis.RedisError as exc:
            STATUS["state"] = "retrying"
            STATUS["error"] = f"{type(exc).__name__}: {exc}"[:200]
            log.exception("redis read failed, retrying in %ds", _RETRY_S)
            await asyncio.sleep(_RETRY_S)
            continue
        STATUS["state"] = "live"
        STATUS["error"] = None
        if resp:
            await process_batch(r, resp[0][1])
