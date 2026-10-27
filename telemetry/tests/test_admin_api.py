"""The admin read API: who may call it, and that every answer is right."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from auth import backend
from tests.helpers import seed, token_for

URL = "/api/v1/telemetry"


def ago(**kw) -> datetime:
    return datetime.now(UTC) - timedelta(**kw)


async def get(client, endpoint, token, **params):
    return await client.get(
        f"{URL}{endpoint}", params=params, headers={"authorization": f"Bearer {token}"}
    )


# --------------------------------------------------------------- access control
@pytest.mark.parametrize(
    "path",
    [
        "/events",
        "/events/facets",
        "/events/histogram",
        "/llm",
        "/sessions",
        "/users",
        "/overview",
        "/events/export",
    ],
)
async def test_every_admin_endpoint_needs_a_signed_in_admin(client, admin_token, path):
    assert (await client.get(f"{URL}{path}")).status_code == 401
    assert (
        await client.get(f"{URL}{path}", headers={"authorization": "Bearer junk"})
    ).status_code == 401
    forged = token_for("x", secret="wrong-secret-wrong-secret-wrong-secret")
    assert (await get(client, path, forged)).status_code == 401
    ordinary = token_for("just-a-person")  # a valid token, but the backend says: not an admin
    assert (await get(client, path, ordinary)).status_code == 403
    assert (await get(client, path, admin_token)).status_code == 200


async def test_the_health_probe_is_open_but_the_detailed_checks_are_not(client, admin_token):
    assert (await client.get("/api/v1/health")).json() == {"status": "ok", "database": True}
    assert (await client.get("/api/v1/health/checks")).status_code == 401
    r = await get(client, "/../health/checks", admin_token)  # path join sanity
    del r
    r = await client.get(
        "/api/v1/health/checks", headers={"authorization": f"Bearer {admin_token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert (
        body["database"]["ok"]
        and body["redis"]["ok"]
        and "consumer" in body
        and body["stored"]["events"] == 0
    )


async def test_an_unreachable_backend_is_a_503_not_a_free_pass(client, monkeypatch):
    async def down(token):
        raise backend.BackendUnavailable("down")

    monkeypatch.setattr(backend, "is_admin", down)
    r = await get(client, "/events", token_for("someone"))
    assert r.status_code == 503


async def test_admin_status_is_cached_briefly_and_revocation_takes_effect(client, monkeypatch):
    calls = []
    answers = iter([True, False])

    async def verdict(token):
        calls.append(token)
        return next(answers)

    # exercise the real cache around a faked HTTP answer
    import httpx

    class FakeResponse:
        def __init__(self, admin):
            self.status_code = 200
            self._admin = admin

        def json(self):
            return {"is_admin": self._admin}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            calls.append(1)
            return FakeResponse(next(answers))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    token = token_for("admin-x")
    assert await backend.is_admin(token) is True
    assert await backend.is_admin(token) is True  # cached: no second call
    assert len(calls) == 1
    backend.reset_caches()
    assert await backend.is_admin(token) is False  # after the cache lapses, revocation shows


# ------------------------------------------------------------------ the event list
async def test_events_come_newest_first_with_the_readable_email(client, admin_token):
    await seed(
        {"name": "old", "created_at": ago(minutes=30), "user_id": "u1"},
        {"name": "new", "created_at": ago(minutes=1), "user_id": "u2"},
    )
    body = (await get(client, "/events", admin_token)).json()
    assert [e["name"] for e in body["events"]] == ["new", "old"]
    assert body["events"][0]["user_email"] == "u2@example.test"
    assert body["total"] is None and body["latest_seq"] == 2
    assert (await get(client, "/events", admin_token, include_total="true")).json()["total"] == 2


async def test_the_default_window_is_24_hours_and_ranges_change_it(client, admin_token):
    await seed(
        {"name": "recent", "created_at": ago(minutes=10)},
        {"name": "yesterday", "created_at": ago(hours=30)},
        {"name": "last_week", "created_at": ago(days=5)},
    )
    names = lambda r: sorted(e["name"] for e in r.json()["events"])  # noqa: E731
    assert names(await get(client, "/events", admin_token)) == ["recent"]
    assert names(await get(client, "/events", admin_token, range="7d")) == [
        "last_week",
        "recent",
        "yesterday",
    ]
    assert names(await get(client, "/events", admin_token, range="15m")) == ["recent"]
    assert (await get(client, "/events", admin_token, range="1y")).status_code == 422


async def test_an_explicit_window_overrides_the_preset(client, admin_token):
    await seed(
        {"name": "a", "created_at": ago(hours=3)}, {"name": "b", "created_at": ago(minutes=1)}
    )
    r = await get(
        client,
        "/events",
        admin_token,
        since=ago(hours=4).isoformat(),
        until=ago(hours=2).isoformat(),
    )
    assert [e["name"] for e in r.json()["events"]] == ["a"]
    bad = await get(
        client,
        "/events",
        admin_token,
        since=ago(hours=1).isoformat(),
        until=ago(hours=2).isoformat(),
    )
    assert bad.status_code == 422
    assert (await get(client, "/events", admin_token, since="yesterday-ish")).status_code == 422


async def test_every_filter_narrows_the_list(client, admin_token):
    await seed(
        {"name": "api_request", "source": "backend", "level": "info", "outcome": "ok", "user_id": "u1",
         "session_id": "s1", "request_id": "r1", "path": "/api/projects", "platform": "desktop"},
        {"name": "click", "source": "frontend", "level": "info", "user_id": "u1", "session_id": "s1", "platform": "desktop"},
        {"name": "js_error", "source": "frontend", "level": "error", "outcome": "error", "user_id": None,
         "session_id": "s2", "platform": "mobile"},
        {"name": "llm.script", "source": "backend", "event_type": "llm_usage", "user_id": "u2", "outcome": "ok"},
        {"name": "render_job", "source": "worker", "event_type": "log", "level": "warning", "user_id": "u2"},
    )  # fmt: skip

    async def names(**params):
        r = await get(client, "/events", admin_token, **params)
        assert r.status_code == 200, r.text
        return sorted(e["name"] for e in r.json()["events"])

    assert await names(source="frontend") == ["click", "js_error"]
    assert await names(source=["frontend", "worker"]) == ["click", "js_error", "render_job"]
    assert await names(event_type="llm_usage") == ["llm.script"]
    assert await names(name="click") == ["click"]
    assert await names(name=["click", "js_error"]) == ["click", "js_error"]
    assert await names(level="error") == ["js_error"]
    assert await names(level=["error", "warning"]) == ["js_error", "render_job"]
    assert await names(outcome="ok") == ["api_request", "llm.script"]
    assert await names(user="u1") == ["api_request", "click"]
    assert await names(anonymous="true") == ["js_error"]
    assert await names(anonymous="false") == ["api_request", "click", "llm.script", "render_job"]
    assert await names(session="s1") == ["api_request", "click"]
    assert await names(request_id="r1") == ["api_request"]
    assert await names(path="projects") == ["api_request"]
    assert await names(platform="mobile") == ["js_error"]
    assert await names(hide="click") == ["api_request", "js_error", "llm.script", "render_job"]
    assert await names(source="backend", level="info", user="u1") == ["api_request"]
    assert await names(user="nobody") == []


async def test_search_finds_names_paths_ids_and_property_text(client, admin_token):
    await seed(
        {"name": "scene_split", "props": {"scene": "intro"}},
        {"name": "page_view", "path": "/projects/abc"},
        {"name": "other", "user_id": "needle-user"},
        {"name": "other2", "session_id": "needle-session"},
        {"name": "other3", "request_id": "needle-req"},
        {"name": "boring", "props": {"note": "nothing"}},
    )

    async def found(q):
        return sorted(
            e["name"] for e in (await get(client, "/events", admin_token, q=q)).json()["events"]
        )

    assert await found("split") == ["scene_split"]
    assert await found("intro") == ["scene_split"]  # inside the properties
    assert await found("projects/abc") == ["page_view"]
    assert await found("needle-user") == ["other"]
    assert await found("needle-session") == ["other2"]
    assert await found("needle-req") == ["other3"]
    assert await found("NOTHING") == ["boring"]  # case-insensitive
    assert await found("zzz") == []


async def test_search_treats_wildcards_literally(client, admin_token):
    await seed({"name": "a_b"}, {"name": "axb"}, {"name": "100%"}, {"name": "1000"})
    got = lambda r: sorted(e["name"] for e in r.json()["events"])  # noqa: E731
    assert got(await get(client, "/events", admin_token, q="a_b")) == ["a_b"]  # _ is not "any char"
    assert got(await get(client, "/events", admin_token, q="100%")) == [
        "100%"
    ]  # % is not "anything"


async def test_paging_walks_the_whole_history_without_gaps_or_repeats(client, admin_token):
    same_moment = ago(minutes=10)
    await seed(
        *[
            {"name": f"e{i:02d}", "created_at": same_moment if i % 3 else ago(minutes=i + 11)}
            for i in range(25)
        ]
    )
    seen, cursor = [], None
    for _ in range(10):
        params = {"limit": 7, **({"before": cursor} if cursor else {})}
        body = (await get(client, "/events", admin_token, **params)).json()
        seen += [e["name"] for e in body["events"]]
        cursor = body["next_before"]
        if not cursor:
            break
    assert len(seen) == 25 and len(set(seen)) == 25  # events sharing a timestamp are not skipped


async def test_the_live_tail_returns_only_what_arrived_after_a_point(client, admin_token):
    await seed({"name": "first"}, {"name": "second"})
    latest = (await get(client, "/events", admin_token)).json()["latest_seq"]
    assert (await get(client, "/events", admin_token, after_seq=latest)).json()["events"] == []
    await seed({"name": "third", "created_at": ago(hours=2)})  # arrives now, but happened earlier
    body = (await get(client, "/events", admin_token, after_seq=latest, range="7d")).json()
    assert [e["name"] for e in body["events"]] == ["third"]
    assert body["latest_seq"] == latest + 1


async def test_the_page_size_is_bounded(client, admin_token):
    assert (await get(client, "/events", admin_token, limit=501)).status_code == 422
    assert (await get(client, "/events", admin_token, limit=0)).status_code == 422


# ------------------------------------------------------------------------ facets
async def test_facets_count_under_the_current_filters_but_show_alternatives(client, admin_token):
    await seed(
        {"name": "a", "source": "frontend", "level": "info"},
        {"name": "a", "source": "frontend", "level": "error"},
        {"name": "b", "source": "backend", "level": "info"},
        {"name": "c", "source": "worker", "level": "info", "user_id": "u"},
    )
    facets = (await get(client, "/events/facets", admin_token, source="frontend")).json()
    assert facets["total"] == 2
    as_dict = lambda key: {x["value"]: x["count"] for x in facets[key]}  # noqa: E731
    # the source facet ignores its own filter, so the other sources stay visible...
    assert as_dict("source") == {"frontend": 2, "backend": 1, "worker": 1}
    # ...while every other facet is counted inside the chosen source
    assert as_dict("level") == {"info": 1, "error": 1}
    assert as_dict("name") == {"a": 2}
    assert facets["anonymous"] == 2


async def test_facet_names_are_ranked_and_limited(client, admin_token):
    await seed(*[{"name": f"n{i}"} for i in range(5)], *[{"name": "popular"}] * 3)
    names = (await get(client, "/events/facets", admin_token)).json()["name"]
    assert names[0] == {"value": "popular", "count": 3}


# --------------------------------------------------------------------- histogram
async def test_the_histogram_has_a_bucket_for_every_slot_and_adds_up(client, admin_token):
    await seed(
        {"created_at": ago(minutes=2), "source": "frontend"},
        {"created_at": ago(minutes=2), "source": "backend", "level": "error"},
        {"created_at": ago(minutes=40), "source": "worker"},
    )
    body = (await get(client, "/events/histogram", admin_token, range="1h")).json()
    buckets = body["buckets"]
    assert body["bucket_seconds"] == 60 and 60 <= len(buckets) <= 62
    stamps = [datetime.fromisoformat(b["t"]) for b in buckets]
    assert all((b - a).total_seconds() == 60 for a, b in zip(stamps, stamps[1:], strict=False))
    assert sum(b["total"] for b in buckets) == 3
    assert (
        sum(b["frontend"] for b in buckets),
        sum(b["backend"] for b in buckets),
        sum(b["worker"] for b in buckets),
    ) == (1, 1, 1)
    assert sum(b["errors"] for b in buckets) == 1
    assert any(b["total"] == 0 for b in buckets)  # quiet minutes are visible zeros


async def test_the_histogram_respects_the_same_filters_as_the_list(client, admin_token):
    await seed({"source": "frontend", "name": "x"}, {"source": "backend", "name": "y"})
    body = (await get(client, "/events/histogram", admin_token, source="backend")).json()
    assert sum(b["total"] for b in body["buckets"]) == 1


# --------------------------------------------------- one event, and what shares its request
async def test_an_event_shows_everything_that_shares_its_request_id(client, admin_token):
    await seed(
        {
            "name": "network_request",
            "source": "frontend",
            "request_id": "req-001",
            "created_at": ago(seconds=30),
        },
        {
            "name": "api_request",
            "source": "backend",
            "request_id": "req-001",
            "created_at": ago(seconds=29),
        },
        {
            "name": "scene_updated",
            "source": "backend",
            "request_id": "req-001",
            "created_at": ago(seconds=29),
        },
        {"name": "unrelated", "request_id": "req-002"},
    )
    first = (await get(client, "/events", admin_token, name="network_request")).json()["events"][0]
    body = (await get(client, f"/events/{first['id']}", admin_token)).json()
    assert body["event"]["name"] == "network_request"
    assert [e["name"] for e in body["same_request"]] == ["api_request", "scene_updated"]


async def test_unknown_or_malformed_event_ids(client, admin_token):
    assert (await get(client, f"/events/{uuid.uuid4()}", admin_token)).status_code == 404
    assert (await get(client, "/events/not-a-uuid", admin_token)).status_code == 422


# ------------------------------------------------------------------------- export
async def test_export_as_json_and_csv(client, admin_token):
    await seed(
        {"name": "a,b", "props": {"k": "v, with comma"}, "user_id": "u1"}, {"name": "second"}
    )
    j = await get(client, "/events/export", admin_token, format="json")
    assert j.headers["content-disposition"].startswith('attachment; filename="events-')
    assert {e["name"] for e in j.json()} == {"a,b", "second"}

    c = await get(client, "/events/export", admin_token, format="csv")
    assert c.headers["content-type"].startswith("text/csv")
    import csv
    import io

    rows = list(csv.DictReader(io.StringIO(c.text)))
    assert {r["name"] for r in rows} == {"a,b", "second"}  # the comma did not split the field
    assert '"k": "v, with comma"' in next(r for r in rows if r["name"] == "a,b")["properties"]
    assert (await get(client, "/events/export", admin_token, format="xml")).status_code == 422
    filtered = await get(client, "/events/export", admin_token, format="json", name="second")
    assert [e["name"] for e in filtered.json()] == ["second"]


# ----------------------------------------------------------------- sessions, users
async def test_sessions_summarise_and_the_timeline_interleaves_browser_and_server(
    client, admin_token
):
    await seed(
        {"name": "page_view", "source": "frontend", "session_id": "S1", "user_id": "u1", "created_at": ago(minutes=9), "platform": "desktop"},
        {"name": "click", "source": "frontend", "session_id": "S1", "user_id": "u1", "created_at": ago(minutes=8)},
        {"name": "api_request", "source": "backend", "session_id": "S1", "user_id": "u1", "created_at": ago(minutes=8, seconds=-1)},
        {"name": "js_error", "source": "frontend", "session_id": "S1", "level": "error", "created_at": ago(minutes=5)},
        {"name": "page_view", "source": "frontend", "session_id": "S2", "created_at": ago(minutes=2)},
        {"name": "no_session"},
    )  # fmt: skip
    sessions = (await get(client, "/sessions", admin_token)).json()["sessions"]
    assert [s["session_id"] for s in sessions] == ["S2", "S1"]  # most recent activity first
    s1 = sessions[1]
    assert (s1["events"], s1["errors"], s1["pages"], s1["backend_events"]) == (4, 1, 1, 1)
    assert s1["user_id"] == "u1" and s1["user_email"] == "u1@example.test"
    assert s1["duration_s"] == pytest.approx(4 * 60, abs=2)
    assert sessions[0]["user_id"] is None

    timeline = (await get(client, "/sessions/S1/timeline", admin_token)).json()
    assert [e["name"] for e in timeline["events"]] == [
        "page_view",
        "click",
        "api_request",
        "js_error",
    ]
    assert [e["source"] for e in timeline["events"]] == [
        "frontend",
        "frontend",
        "backend",
        "frontend",
    ]
    assert timeline["user_email"] == "u1@example.test"
    assert (await get(client, "/sessions/nope/timeline", admin_token)).status_code == 404


async def test_users_are_listed_with_activity_and_detail(client, admin_token):
    await seed(
        {"name": "a", "user_id": "u1", "session_id": "s1", "created_at": ago(minutes=20)},
        {
            "name": "b",
            "user_id": "u1",
            "session_id": "s2",
            "level": "error",
            "created_at": ago(minutes=3),
        },
        {"name": "a", "user_id": "u1", "session_id": "s2", "created_at": ago(minutes=2)},
        {"name": "c", "user_id": "u2"},
        {"name": "anon"},
    )
    users = (await get(client, "/users", admin_token)).json()["users"]
    assert [u["user_id"] for u in users] == ["u2", "u1"] or [u["user_id"] for u in users] == [
        "u1",
        "u2",
    ]
    u1 = next(u for u in users if u["user_id"] == "u1")
    assert (u1["events"], u1["sessions"], u1["errors"]) == (3, 2, 1) and u1[
        "user_email"
    ] == "u1@example.test"
    assert all(u["user_id"] for u in users)  # anonymous traffic is not a "user"

    detail = (await get(client, "/users/u1", admin_token)).json()
    assert detail["user"]["events"] == 3
    assert {t["name"]: t["count"] for t in detail["top_events"]} == {"a": 2, "b": 1}
    assert [e["name"] for e in detail["errors"]] == ["b"]
    assert {s["session_id"] for s in detail["sessions"]} == {"s1", "s2"}
    assert (await get(client, "/users/ghost", admin_token)).status_code == 404


async def test_the_user_filter_works_alongside_the_path_parameter(client, admin_token):
    # regression: a query filter named like the path parameter used to stop the app starting
    await seed({"name": "a", "user_id": "u1"}, {"name": "b", "user_id": "u2"})
    assert (await get(client, "/users/u1", admin_token, source="backend")).status_code == 200
    assert (await get(client, "/sessions/zzz/timeline", admin_token, user="u1")).status_code == 404


# ------------------------------------------------------------------------ overview
async def test_the_overview_adds_up_the_pipeline(client, admin_token):
    api = [
        {
            "name": "api_request",
            "source": "backend",
            "duration_ms": d,
            "outcome": "ok",
            "user_id": "u1",
            "session_id": "s1",
        }
        for d in (10, 20, 30, 40, 100)
    ]
    await seed(
        *api,
        {"name": "api_request", "source": "backend", "duration_ms": 50, "outcome": "error", "level": "error"},
        {"name": "llm.script", "event_type": "llm_usage", "source": "backend", "provider": "gemini", "model": "m",
         "total_tokens": 1000, "cost_usd": 0.01, "duration_ms": 4000, "outcome": "ok"},
        {"name": "llm.script", "event_type": "llm_usage", "source": "backend", "provider": "gemini", "model": "m",
         "total_tokens": 500, "cost_usd": 0.005, "duration_ms": 6000, "outcome": "error"},
        {"name": "render_job", "source": "worker", "duration_ms": 20_000, "outcome": "ok"},
        {"name": "render_job", "source": "worker", "duration_ms": 40_000, "outcome": "ok"},
        {"name": "render_job", "source": "worker", "duration_ms": 1_000, "outcome": "error", "level": "error"},
        {"name": "web_vital", "source": "frontend", "props": {"metric": "LCP", "value": 1000}},
        {"name": "web_vital", "source": "frontend", "props": {"metric": "LCP", "value": 3000}},
        {"name": "click", "source": "frontend", "user_id": "u2", "session_id": "s2"},
    )  # fmt: skip
    body = (await get(client, "/overview", admin_token)).json()

    t = body["totals"]
    assert t["events"] == 14 and t["errors"] == 2 and t["users"] == 2 and t["sessions"] == 2
    assert body["by_source"] == {"backend": 8, "worker": 3, "frontend": 3}
    api = body["api"]
    assert api["requests"] == 6 and api["errors"] == 1
    assert api["p50_ms"] == pytest.approx(35)  # 10,20,30,40,50,100
    assert api["p95_ms"] == pytest.approx(87.5)  # 50 + 0.75 * (100 - 50)
    llm = body["llm"]
    assert (llm["calls"], llm["failures"], llm["tokens"]) == (2, 1, 1500)
    assert llm["cost_usd"] == pytest.approx(0.015) and llm["avg_ms"] == pytest.approx(5000)
    assert llm["by_model"][0]["model"] == "m" and llm["by_model"][0]["calls"] == 2
    r = body["renders"]
    assert (r["jobs"], r["failed"]) == (3, 1) and r["avg_ms"] == pytest.approx(30_000)
    assert body["web_vitals"] == [{"metric": "LCP", "samples": 2, "p75": 2500.0}]
    assert body["top_events"][0] == {"name": "api_request", "count": 6}
    assert sum(b["total"] for b in body["histogram"]["buckets"]) == 14


async def test_an_empty_system_gives_empty_answers_not_errors(client, admin_token):
    for path in (
        "/overview",
        "/events",
        "/events/facets",
        "/events/histogram",
        "/sessions",
        "/users",
    ):
        r = await get(client, path, admin_token)
        assert r.status_code == 200, (path, r.text)
    body = (await get(client, "/overview", admin_token)).json()
    assert (
        body["totals"]["events"] == 0
        and body["api"]["p50_ms"] is None
        and body["llm"]["cost_usd"] is None
    )


# --------------------------------------------------------------------------- llm
async def test_llm_usage_adds_up_by_model_and_person(client, admin_token):
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    llm = {"event_type": "llm_usage", "name": "llm.script", "provider": "gemini", "model": "g1"}
    await seed(
        {**llm, "user_id": a, "outcome": "ok", "duration_ms": 100, "total_tokens": 300,
         "prompt_tokens": 100, "completion_tokens": 200, "cost_usd": 0.01},
        {**llm, "user_id": a, "outcome": "ok", "duration_ms": 300, "total_tokens": 100,
         "prompt_tokens": 50, "completion_tokens": 50, "cost_usd": 0.02},
        {**llm, "user_id": b, "outcome": "error", "level": "error", "duration_ms": 50},
        {"name": "api_request", "user_id": a},  # not an AI event: must not count
    )
    body = (await get(client, "/llm", admin_token, range="1h")).json()
    t = body["totals"]
    assert (t["calls"], t["failures"], t["tokens"], t["users"]) == (3, 1, 400, 2)
    assert t["prompt_tokens"] == 150 and t["completion_tokens"] == 250
    assert t["cost_usd"] == pytest.approx(0.03)
    [model] = body["by_model"]
    assert (model["call"], model["calls"], model["failures"]) == ("llm.script", 3, 1)
    top = body["by_user"][0]
    assert (top["user_id"], top["calls"], top["tokens"]) == (a, 2, 400)
    assert len(body["recent_failures"]) == 1
    assert sum(p["calls"] for p in body["series"]) == 3
    assert sum(p["tokens"] for p in body["series"]) == 400


async def test_llm_usage_respects_the_user_filter(client, admin_token):
    a = str(uuid.uuid4())
    llm = {"event_type": "llm_usage", "name": "llm.script", "outcome": "ok"}
    await seed({**llm, "user_id": a}, {**llm, "user_id": str(uuid.uuid4())})
    body = (await get(client, "/llm", admin_token, range="1h", user=a)).json()
    assert body["totals"]["calls"] == 1
