"""Render job creation, the composition payload, and status reporting.

The renderer itself is NOT invoked here (that needs Chromium and minutes of CPU);
what is tested is everything around it: validation, job rows, the payload
contract, progress reporting and ownership.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.services.render_payload import build_composition_payload


async def test_render_requires_scenes(auth_client: AsyncClient, project: dict) -> None:
    response = await auth_client.post(f"/api/projects/{project['id']}/render")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROJECT_EMPTY"


async def test_render_creates_a_queued_job(
    auth_client: AsyncClient, project: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.render_service as render_module

    enqueued: list[tuple] = []

    async def fake_enqueue(task: str, *args: object, **kwargs: object) -> str:
        enqueued.append((task, args))
        return "job-1"

    # Patch the symbol where it is imported inside create_job.
    monkeypatch.setattr("app.services.queue.enqueue", fake_enqueue)
    assert render_module  # module imported for clarity

    await auth_client.post(
        f"/api/projects/{project['id']}/scenes", json={"narration": "a", "duration": 3}
    )

    response = await auth_client.post(f"/api/projects/{project['id']}/render")
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert enqueued and enqueued[0][0] == "render_project"

    job = (await auth_client.get(f"/api/render-jobs/{body['job_id']}")).json()
    assert job["progress"] == 0
    assert job["output_url"] is None

    # The project is marked as rendering so the dashboard can show it.
    assert (await auth_client.get(f"/api/projects/{project['id']}")).json()["status"] == "rendering"


async def test_render_job_is_private_to_its_owner(
    client: AsyncClient, auth_client: AsyncClient, project: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.queue.enqueue", lambda *a, **k: _noop())

    async def _noop() -> None:
        return None

    await auth_client.post(
        f"/api/projects/{project['id']}/scenes", json={"narration": "a", "duration": 3}
    )
    created = await auth_client.post(f"/api/projects/{project['id']}/render")
    job_id = created.json()["job_id"]

    other = await client.post(
        "/api/auth/register",
        json={"email": f"o{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    response = await client.get(f"/api/render-jobs/{job_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RENDER_JOB_NOT_FOUND"


async def test_unknown_render_job_is_404(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"/api/render-jobs/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_composition_payload_shape(session, auth_client: AsyncClient, project: dict) -> None:
    """The payload is the backend/renderer contract: verify it precisely."""
    from sqlalchemy import select

    from app.models.project import Project
    from app.repositories.project_repository import ProjectRepository

    await auth_client.post(
        f"/api/projects/{project['id']}/scenes",
        json={"narration": "hello world", "duration": 4, "on_screen_text": "Title",
              "transition": "fade"},
    )
    await auth_client.post(
        f"/api/projects/{project['id']}/scenes", json={"narration": "second", "duration": 2.5}
    )

    row = (
        await session.execute(select(Project).where(Project.id == uuid.UUID(project["id"])))
    ).scalar_one()
    loaded = await ProjectRepository(session).get_for_owner(row.id, row.owner_id)
    payload = build_composition_payload(loaded)

    assert payload["project"] == {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "title": loaded.title,
        "language": "en",
    }
    assert [scene["duration"] for scene in payload["scenes"]] == [4.0, 2.5]
    first = payload["scenes"][0]
    # Exactly the keys the renderer's zod schema expects.
    assert set(first) == {
        "id", "duration", "visualUrl", "audioUrl", "onScreenText",
        "captions", "transition", "backgroundColor",
    }
    assert first["onScreenText"] == "Title"
    assert first["visualUrl"] is None  # no image generated in this test
    assert first["captions"][0]["start"] == 0.0
