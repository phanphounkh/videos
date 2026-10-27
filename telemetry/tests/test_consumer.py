"""The Redis stream consumer: persistence, poison entries, crash recovery."""

import asyncio
import json

from app.config import get_settings
from app.ingest import consumer
from tests.helpers import all_events


def entry(**fields) -> dict:
    base = {"event_type": "product", "name": "thing_happened"}
    return {"payload": json.dumps({**base, **fields})}


async def deliver(r, *payloads: dict):
    """XADD entries, then hand them to the consumer exactly as XREADGROUP would."""
    settings = get_settings()
    for payload in payloads:
        await r.xadd(settings.telemetry_stream_key, payload)
    await consumer._ensure_group(r)
    resp = await r.xreadgroup(
        settings.telemetry_consumer_group, "t1", {settings.telemetry_stream_key: ">"}, count=100
    )
    return resp[0][1]


async def pending(r) -> int:
    settings = get_settings()
    info = await r.xpending(settings.telemetry_stream_key, settings.telemetry_consumer_group)
    return int(info["pending"])


async def test_entries_become_rows_and_are_acknowledged(stream):
    entries = await deliver(
        stream,
        entry(name="a", source="backend", level="warning", user_id="u1", session_id="s1"),
        entry(name="b", source="worker", event_type="log", duration_ms=12),
    )
    await consumer.process_batch(stream, entries)
    rows = await all_events()
    assert [(r["name"], r["source"], r["level"]) for r in rows] == [
        ("a", "backend", "warning"),
        ("b", "worker", "info"),
    ]
    assert rows[0]["user_id"] == "u1" and rows[1]["duration_ms"] == 12
    assert await pending(stream) == 0


async def test_llm_usage_fields_survive(stream):
    entries = await deliver(
        stream,
        entry(
            event_type="llm_usage", name="llm.script", provider="gemini", model="m",
            prompt_tokens=100, completion_tokens=40, total_tokens=140, cost_usd=0.0123,
            duration_ms=5000, outcome="ok",
        ),
    )  # fmt: skip
    await consumer.process_batch(stream, entries)
    [row] = await all_events()
    assert (row["provider"], row["total_tokens"], row["cost_usd"]) == ("gemini", 140, 0.0123)


async def test_the_event_time_is_when_it_happened_not_when_it_arrived(stream):
    import time

    then = time.time() - 120
    entries = await deliver(stream, entry(ts=then))
    await consumer.process_batch(stream, entries)
    [row] = await all_events()
    assert abs(row["created_at"].timestamp() - then) < 1


async def test_malformed_entries_are_dropped_and_acknowledged_not_retried_forever(stream):
    before = dict(consumer.STATUS)
    entries = await deliver(
        stream,
        {"payload": "{not json"},
        {"payload": json.dumps([1, 2, 3])},  # JSON, but not an object
        {"nothing": "here"},  # no payload field at all
        entry(name="unknown_field", surprise=1),  # extra="forbid": drift is caught loudly
        entry(event_type="not-a-type"),
        entry(name="good"),
    )
    await consumer.process_batch(stream, entries)
    assert [r["name"] for r in await all_events()] == ["good"]
    assert consumer.STATUS["dropped"] - before["dropped"] == 5
    assert consumer.STATUS["persisted"] - before["persisted"] == 1
    assert await pending(stream) == 0  # a poison pill must never block what is behind it


async def test_a_row_the_database_refuses_does_not_cost_the_rest_of_the_batch(stream):
    before = dict(consumer.STATUS)
    entries = await deliver(
        stream,
        entry(name="before"),
        entry(name="overflow", prompt_tokens=2**40),  # does not fit an INTEGER column
        entry(name="after"),
    )
    await consumer.process_batch(stream, entries)
    assert [r["name"] for r in await all_events()] == ["before", "after"]
    assert consumer.STATUS["rejected"] - before["rejected"] == 1
    assert await pending(stream) == 0


async def test_nul_bytes_and_emails_in_free_text_are_made_safe(stream):
    entries = await deliver(
        stream,
        entry(
            properties={
                "error": "bad\u0000thing for me@example.com",
                "tok": "Bearer abcdefgh12345678",
            }
        ),
    )
    await consumer.process_batch(stream, entries)
    [row] = await all_events()
    assert row["properties"]["error"] == "badthing for [email]"
    assert row["properties"]["tok"] == "[token]"


async def test_entries_delivered_but_never_acknowledged_are_reclaimed_after_a_crash(stream):
    settings = get_settings()
    await deliver(stream, entry(name="orphan-1"), entry(name="orphan-2"))
    assert await pending(stream) == 2  # delivered to consumer t1, never processed: it "crashed"

    settings_name = settings.hostname
    try:
        settings.hostname = "t1"  # the restarted container has the same stable name
        task = asyncio.create_task(consumer.consume_forever())
        for _ in range(50):
            await asyncio.sleep(0.1)
            if len(await all_events()) == 2:
                break
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    finally:
        settings.hostname = settings_name
    assert sorted(r["name"] for r in await all_events()) == ["orphan-1", "orphan-2"]
    assert await pending(stream) == 0


async def test_the_live_loop_picks_up_new_events_and_reports_its_state(stream):
    task = asyncio.create_task(consumer.consume_forever())
    try:
        for _ in range(50):
            await asyncio.sleep(0.1)
            if consumer.STATUS["state"] == "live":
                break
        assert consumer.STATUS["state"] == "live"
        await stream.xadd(get_settings().telemetry_stream_key, entry(name="live_one"))
        for _ in range(60):
            await asyncio.sleep(0.1)
            if await all_events():
                break
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert [r["name"] for r in await all_events()] == ["live_one"]
    assert consumer.STATUS["state"] == "not_started"  # cancelled cleanly
