"""The backend as a telemetry PRODUCER: what reaches the Redis stream, and what never does.

Real Redis, a private stream per test; the telemetry service itself is not involved
(it has its own suite). These tests pin the contract: shape, context stamping,
scrubbing, and the rule that telemetry can never break or block the caller.
"""

import json
import uuid
from collections.abc import AsyncIterator

import pytest
import redis.asyncio as redis
from httpx import AsyncClient

from app.core.config import get_settings
from app.services.telemetry import context
from app.services.telemetry.ai import track_ai
from app.services.telemetry.events import Event
from app.services.telemetry.recorder import Recorder, get_recorder, record


@pytest.fixture
async def stream(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator["Stream"]:
    key = f"test:telemetry:{uuid.uuid4().hex}"
    monkeypatch.setenv("TELEMETRY_STREAM_KEY", key)
    base = get_settings().redis_url.rsplit("/", 1)[0]
    monkeypatch.setenv("REDIS_URL", f"{base}/15")
    get_settings.cache_clear()
    client = redis.Redis.from_url(f"{base}/15", decode_responses=True)
    yield Stream(client, key)
    await client.delete(key)
    await client.aclose()
    await get_recorder().stop()
    get_settings.cache_clear()


class Stream:
    def __init__(self, client: redis.Redis, key: str) -> None:
        self.client, self.key = client, key

    async def events(self) -> list[dict]:
        await get_recorder().flush()
        entries = await self.client.xrange(self.key)
        return [json.loads(fields["payload"]) for _, fields in entries]

    async def named(self, name: str) -> list[dict]:
        return [e for e in await self.events() if e["name"] == name]


async def test_event_is_written_in_the_wire_shape(stream: Stream) -> None:
    record(Event(name="thing_happened", properties={"n": 1}))
    [event] = await stream.named("thing_happened")
    assert event["event_type"] == "product"
    assert event["source"] == "backend"
    assert event["properties"] == {"n": 1}
    assert isinstance(event["ts"], float)


async def test_ambient_context_stamps_events(stream: Stream) -> None:
    with context.telemetry_context(
        user_id="u-1", session_id="sess-12345678", request_id="r-12345678"
    ):
        record(Event(name="inside"))
    record(Event(name="outside"))
    [inside] = await stream.named("inside")
    [outside] = await stream.named("outside")
    assert (inside["user_id"], inside["session_id"], inside["request_id"]) == (
        "u-1",
        "sess-12345678",
        "r-12345678",
    )
    assert "user_id" not in outside


async def test_secrets_and_emails_never_leave_the_process(stream: Stream) -> None:
    record(
        Event(
            name="leaky",
            properties={
                "note": "contact me at jane@example.com",
                "auth": "Bearer abcdefghijklmnop",
                "password": "hunter2",
                "nested": {"api_key": "sk-123", "ok": "fine"},
            },
        )
    )
    [event] = await stream.named("leaky")
    dumped = json.dumps(event)
    assert "jane@example.com" not in dumped
    assert "abcdefghijklmnop" not in dumped
    assert "hunter2" not in dumped and "sk-123" not in dumped
    assert event["properties"]["nested"]["ok"] == "fine"


async def test_every_request_is_an_event_with_ids(client: AsyncClient, stream: Stream) -> None:
    response = await client.get(
        "/api/purposes",
        headers={"X-Request-ID": "req-abcdef123456", "X-Telemetry-Session": "sess-abcdef123456"},
    )
    assert response.headers["x-request-id"] == "req-abcdef123456"
    [event] = await stream.named("api_request")
    assert event["request_id"] == "req-abcdef123456"
    assert event["session_id"] == "sess-abcdef123456"
    assert event["properties"]["status_code"] == response.status_code
    assert event["path"] == "/api/purposes"


async def test_unauthenticated_failures_are_recorded(client: AsyncClient, stream: Stream) -> None:
    response = await client.get("/api/projects")
    assert response.status_code == 401
    [event] = await stream.named("api_request")
    assert event["outcome"] == "error" and event["level"] == "warning"
    assert "user_id" not in event
    # The server generated an id and handed it back.
    assert response.headers["x-request-id"] == event["request_id"]


async def test_authenticated_request_carries_the_user(
    auth_client: AsyncClient, stream: Stream
) -> None:
    me = (await auth_client.get("/api/auth/me")).json()
    events = await stream.named("api_request")
    assert any(e.get("user_id") == me["id"] for e in events)


async def test_health_probe_is_not_recorded(client: AsyncClient, stream: Stream) -> None:
    await client.get("/api/health")
    assert await stream.named("api_request") == []


async def test_unsafe_request_ids_are_replaced(client: AsyncClient, stream: Stream) -> None:
    response = await client.get("/api/purposes", headers={"X-Request-ID": "bad id\twith spaces"})
    assert response.headers["x-request-id"] != "bad id\twith spaces"


async def test_log_lines_are_forwarded_with_context(stream: Stream) -> None:
    from app.core.logging import configure_logging, get_logger

    configure_logging()
    with context.telemetry_context(request_id="req-logging-1"):
        get_logger("t").warning("something_odd", project_id="p1")
    [event] = await stream.named("something_odd")
    assert event["event_type"] == "log" and event["level"] == "warning"
    assert event["request_id"] == "req-logging-1"
    assert event["properties"]["project_id"] == "p1"


async def test_telemetry_own_logs_are_not_forwarded(stream: Stream) -> None:
    from app.core.logging import configure_logging, get_logger

    configure_logging()
    get_logger("t").warning("telemetry_flush_failed", error="x")
    assert await stream.named("telemetry_flush_failed") == []


async def test_track_ai_emits_llm_usage(stream: Stream) -> None:
    async with track_ai("llm.script", provider="gemini", model="m1", input_units=100) as call:
        call.output_units = 50
    [event] = await stream.named("llm.script")
    assert event["event_type"] == "llm_usage" and event["outcome"] == "ok"
    assert (event["provider"], event["model"]) == ("gemini", "m1")
    assert (event["prompt_tokens"], event["completion_tokens"], event["total_tokens"]) == (
        100,
        50,
        150,
    )


async def test_track_ai_records_failures_and_reraises(stream: Stream) -> None:
    with pytest.raises(ValueError):
        async with track_ai("llm.script", provider="gemini"):
            raise ValueError("boom")
    [event] = await stream.named("llm.script")
    assert event["outcome"] == "error" and event["level"] == "error"
    assert event["properties"]["error_code"] == "ValueError"


async def test_full_queue_drops_new_events_without_blocking() -> None:
    small = Recorder(queue_size=2)
    assert small.record(Event(name="a")) and small.record(Event(name="b"))
    assert small.record(Event(name="c")) is False
    assert small.stats()["dropped"] == 1


async def test_redis_outage_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    get_settings.cache_clear()
    try:
        rec = Recorder()
        rec.record(Event(name="x"))
        await rec.flush()  # must not raise
        assert rec.stats()["failed"] == 1
        await rec.stop()
    finally:
        get_settings.cache_clear()


async def test_disabled_telemetry_emits_nothing(
    monkeypatch: pytest.MonkeyPatch, stream: Stream
) -> None:
    monkeypatch.setenv("TELEMETRY_ENABLED", "false")
    get_settings.cache_clear()
    assert record(Event(name="nope")) is False
    assert await stream.events() == []
