"""Project CRUD and cross-user isolation."""

import uuid

from httpx import AsyncClient


async def test_create_and_read_project(auth_client: AsyncClient) -> None:
    created = await auth_client.post(
        "/api/projects",
        json={"title": "Khmer history", "language": "km", "aspect_ratio": "9:16"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "draft"
    assert (body["width"], body["height"]) == (1080, 1920)  # 9:16 dimensions

    fetched = await auth_client.get(f"/api/projects/{body['id']}")
    assert fetched.json()["title"] == "Khmer history"


async def test_patch_only_changes_provided_fields(auth_client: AsyncClient, project: dict) -> None:
    updated = await auth_client.patch(f"/api/projects/{project['id']}", json={"title": "Renamed"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"
    assert updated.json()["language"] == project["language"]


async def test_duplicate_copies_scenes(auth_client: AsyncClient, project: dict) -> None:
    await auth_client.post(
        f"/api/projects/{project['id']}/scenes", json={"narration": "one", "duration": 4}
    )
    copy = await auth_client.post(f"/api/projects/{project['id']}/duplicate")
    assert copy.status_code == 201
    assert copy.json()["title"].endswith("(copy)")
    assert copy.json()["scene_count"] == 1


async def test_delete_removes_the_project(auth_client: AsyncClient, project: dict) -> None:
    assert (await auth_client.delete(f"/api/projects/{project['id']}")).status_code == 204
    assert (await auth_client.get(f"/api/projects/{project['id']}")).status_code == 404


async def test_a_user_cannot_see_another_users_project(
    client: AsyncClient, auth_client: AsyncClient, project: dict
) -> None:
    other = await client.post(
        "/api/auth/register",
        json={"email": f"o{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    # 404, not 403: a 403 would confirm the id exists.
    assert (await client.get(f"/api/projects/{project['id']}", headers=headers)).status_code == 404
    assert (
        await client.patch(
            f"/api/projects/{project['id']}", json={"title": "hax"}, headers=headers
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/projects/{project['id']}", headers=headers)
    ).status_code == 404


async def test_listing_is_scoped_to_the_owner(
    client: AsyncClient, auth_client: AsyncClient, project: dict
) -> None:
    other = await client.post(
        "/api/auth/register",
        json={"email": f"o{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get("/api/projects", headers=headers)).json()["total"] == 0
