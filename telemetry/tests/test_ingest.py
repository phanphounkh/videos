"""POST /ingest/events: nothing about the sender is trusted."""

import json
import time
import uuid

import pytest

from app.config import get_settings
from tests.helpers import all_events, token_for

SESSION = str(uuid.uuid4())
DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def body(*events, session=SESSION) -> dict:
    return {"session_id": session, "events": list(events)}


def evt(name="page_view", **extra) -> dict:
    return {"name": name, "ts": int(time.time() * 1000), "properties": {"path": "/x"}, **extra}


async def post(client, payload, token=None, **headers):
    h = {"user-agent": DESKTOP, **headers}
    if token:
        h["authorization"] = f"Bearer {token}"
    return await client.post("/api/v1/ingest/events", json=payload, headers=h)


async def test_a_signed_in_batch_is_stored_with_the_identity_from_the_token(client):
    r = await post(client, body(evt("page_view"), evt("click")), token_for("user-7"))
    assert r.status_code == 202 and r.json() == {"accepted": 2, "rejected": 0}
    rows = await all_events()
    assert [x["name"] for x in rows] == ["page_view", "click"]
    for row in rows:
        assert (row["source"], row["event_type"], row["user_id"]) == (
            "frontend",
            "product",
            "user-7",
        )
        assert row["session_id"] == SESSION and row["platform"] == "desktop"


async def test_events_without_a_token_are_kept_anonymously(client):
    # the login page, errors before anyone signed in
    r = await post(client, body(evt("page_view", properties={"path": "/login"})))
    assert r.status_code == 202 and r.json()["accepted"] == 1
    [row] = await all_events()
    assert row["user_id"] is None and row["source"] == "frontend"


async def test_an_expired_or_forged_token_is_treated_as_anonymous_not_rejected(client):
    for bad in (token_for("u", minutes=-5), token_for("u", secret="wrong-secret"), "garbage"):
        assert (await post(client, body(evt()), bad)).status_code == 202
    assert all(r["user_id"] is None for r in await all_events())


async def test_the_body_cannot_name_someone_else_or_claim_to_be_the_server(client):
    forged = evt("page_view")
    forged.update({"user_id": "victim", "source": "backend", "event_type": "llm_usage"})
    forged["properties"] = {"user_id": "victim"}
    await post(client, body(forged), token_for("me"))
    [row] = await all_events()
    assert (row["user_id"], row["source"], row["event_type"]) == ("me", "frontend", "product")


async def test_any_well_formed_name_is_accepted(client):
    names = ["page_view", "editor.split", "ui:click", "network_request", "console_error", "x"]
    r = await post(client, body(*[evt(n) for n in names]))
    assert r.json()["accepted"] == len(names)


@pytest.mark.parametrize(
    "bad",
    [
        {"name": "Click"},  # upper case
        {"name": "1abc"},  # must start with a letter
        {"name": "has space"},
        {"name": "x" * 81},
        {"name": ""},
        {"name": 5},
        {"name": None},
        {"name": "ok", "ts": "yesterday"},
        {"name": "ok", "ts": -1},
        {"name": "ok", "ts": 2**60},
        {"name": "ok", "ts": True},
        {"name": "ok", "level": "fatal"},
        {"name": "ok", "duration_ms": -3},
        {"name": "ok", "duration_ms": 10**9},
        {"name": "ok", "duration_ms": "slow"},
        {"name": "ok", "request_id": "has spaces!"},
        {"name": "ok", "request_id": 5},
        {"name": "ok", "properties": ["not", "a", "dict"]},
        {"name": "ok", "properties": "text"},
        {"name": "ok", "path": 7},
        "just a string",
        None,
        [],
    ],
)
async def test_each_bad_item_is_dropped_on_its_own(client, bad):
    r = await post(client, body(evt("good_one"), bad, evt("good_two")))
    assert r.status_code == 202
    assert r.json() == {"accepted": 2, "rejected": 1}
    assert [x["name"] for x in await all_events()] == ["good_one", "good_two"]


async def test_oversized_and_too_deep_properties_are_dropped(client):
    huge = evt("huge", properties={"blob": "x" * 2000, "more": ["y" * 2000] * 6})
    deep: dict = {}
    cursor = deep
    for _ in range(20):
        cursor["n"] = {}
        cursor = cursor["n"]
    r = await post(client, body(huge, evt("deep", properties=deep), evt("fine")))
    assert r.json() == {"accepted": 1, "rejected": 2}
    assert [x["name"] for x in await all_events()] == ["fine"]


async def test_long_strings_are_cut_and_emails_and_tokens_are_scrubbed(client):
    props = {
        "message": "Could not load jane@example.com's project",
        "auth": "Bearer abcdefgh12345678xyz",
        "long": "z" * 5000,
        "nul": "a\u0000b",
    }
    await post(client, body(evt("js_error", properties=props, path="/p/me@x.io")))
    [row] = await all_events()
    p = row["properties"]
    assert p["message"] == "Could not load [email]'s project"
    assert p["auth"] == "[token]" and len(p["long"]) == 2000 and p["nul"] == "ab"
    assert row["path"] == "/p/[email]"


async def test_error_level_sets_the_outcome_and_levels_are_kept(client):
    await post(client, body(evt("js_error", level="error"), evt("n", level="warning"), evt("d")))
    rows = await all_events()
    assert [(r["level"], r["outcome"]) for r in rows] == [
        ("error", "error"),
        ("warning", None),
        ("info", None),
    ]


async def test_duration_request_id_and_path_become_columns(client):
    rid = "req_ab12CD34"
    await post(
        client, body(evt("network_request", duration_ms=123.7, request_id=rid, path="/api/x"))
    )
    [row] = await all_events()
    assert (row["duration_ms"], row["request_id"], row["path"]) == (123, rid, "/api/x")


async def test_a_wrong_client_clock_does_not_move_an_event_into_the_future(client):
    future = int((time.time() + 86_400) * 1000)
    await post(client, body(evt("a", ts=future)))
    [row] = await all_events()
    assert abs(row["created_at"].timestamp() - time.time()) < 30


@pytest.mark.parametrize("session", ["", "not-a-uuid", 5, None])
async def test_a_bad_session_id_is_a_400(client, session):
    r = await post(client, {"session_id": session, "events": [evt()]})
    assert r.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "x",
        {"session_id": SESSION},
        {"session_id": SESSION, "events": []},
        {"session_id": SESSION, "events": "no"},
    ],
)
async def test_a_malformed_body_is_a_400(client, payload):
    assert (await post(client, payload)).status_code == 400


async def test_a_batch_over_the_limit_is_refused(client):
    limit = get_settings().ingest_max_events_per_batch
    r = await post(client, body(*[evt() for _ in range(limit + 1)]))
    assert r.status_code == 400
    assert (await post(client, body(*[evt() for _ in range(limit)]))).status_code == 202


async def test_invalid_json_is_a_400_not_a_crash(client):
    r = await client.post(
        "/api/v1/ingest/events", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400


async def test_nan_and_infinity_do_not_fail_the_insert(client):
    raw = (
        '{"session_id": "%s", "events": [{"name": "m", "properties": {"v": NaN, "w": Infinity}}]}'
        % SESSION
    )
    r = await client.post(
        "/api/v1/ingest/events", content=raw, headers={"content-type": "application/json"}
    )
    assert r.status_code == 202
    [row] = await all_events()
    assert row["properties"] == {"v": None, "w": None}


async def test_an_oversized_body_is_refused_before_it_is_buffered(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "ingest_max_body_bytes", 1000)
    big = json.dumps(body(evt(properties={"p": "x" * 1500})))
    assert (await post(client, json.loads(big))).status_code == 413


async def test_signed_in_people_are_rate_limited_per_user(client, stream, monkeypatch):
    monkeypatch.setattr(get_settings(), "ingest_rate_limit_max", 3)
    token = token_for("busy")
    codes = [(await post(client, body(evt()), token)).status_code for _ in range(5)]
    assert codes == [202, 202, 202, 429, 429]
    # a different person is unaffected
    assert (await post(client, body(evt()), token_for("calm"))).status_code == 202


async def test_anonymous_clients_are_limited_per_ip_and_more_tightly(client, stream, monkeypatch):
    monkeypatch.setattr(get_settings(), "ingest_anon_rate_limit_max", 2)
    codes = [
        (await post(client, body(evt()), None, **{"x-forwarded-for": "9.9.9.9"})).status_code
        for _ in range(4)
    ]
    assert codes == [202, 202, 429, 429]
    other = await post(client, body(evt()), None, **{"x-forwarded-for": "8.8.8.8"})
    assert other.status_code == 202


async def test_ingest_still_works_when_redis_is_down(client, monkeypatch):
    import redis.asyncio as redis

    from app import ratelimit

    class Down:
        async def incr(self, *a):
            raise redis.ConnectionError("down")

    monkeypatch.setattr(ratelimit, "_client", lambda: Down())
    assert (await post(client, body(evt()), token_for("u"))).status_code == 202
