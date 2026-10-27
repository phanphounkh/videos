"""Folders, favourites, the trash, bulk actions, storage, activity and templates."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update

from app.models.project import Project

PASSWORD = "supersecret123"


async def make(client: AsyncClient, title: str) -> dict:
    r = await client.post("/api/projects", json={"title": title})
    assert r.status_code == 201, r.text
    return r.json()


async def titles(client: AsyncClient, **params) -> list[str]:
    r = await client.get("/api/projects", params=params)
    assert r.status_code == 200, r.text
    return sorted(p["title"] for p in r.json()["items"])


# ----------------------------------------------------------------------- trash
async def test_delete_moves_to_trash_and_restore_brings_it_back(auth_client: AsyncClient) -> None:
    p = await make(auth_client, "Keep me")
    assert (await auth_client.delete(f"/api/projects/{p['id']}")).status_code == 204
    assert await titles(auth_client) == []
    assert await titles(auth_client, view="trash") == ["Keep me"]
    # a trashed project is gone for every other endpoint
    assert (await auth_client.get(f"/api/projects/{p['id']}")).status_code == 404
    restored = await auth_client.post(f"/api/projects/{p['id']}/restore")
    assert restored.status_code == 200 and restored.json()["deleted_at"] is None
    assert await titles(auth_client) == ["Keep me"]
    assert await titles(auth_client, view="trash") == []


async def test_permanent_delete_and_empty_trash(auth_client: AsyncClient) -> None:
    a, b = await make(auth_client, "A"), await make(auth_client, "B")
    assert (await auth_client.delete(f"/api/projects/{a['id']}?permanent=true")).status_code == 204
    assert await titles(auth_client, view="trash") == []
    await auth_client.delete(f"/api/projects/{b['id']}")
    assert (await auth_client.delete("/api/projects/trash")).status_code == 204
    assert await titles(auth_client, view="trash") == []
    assert (await auth_client.post(f"/api/projects/{b['id']}/restore")).status_code == 404


async def test_old_trash_is_purged_when_the_trash_is_opened(
    auth_client: AsyncClient, session
) -> None:
    p = await make(auth_client, "Ancient")
    await auth_client.delete(f"/api/projects/{p['id']}")
    await session.execute(
        update(Project)
        .where(Project.id == uuid.UUID(p["id"]))
        .values(deleted_at=datetime.now(UTC) - timedelta(days=31))
    )
    await session.commit()
    assert await titles(auth_client, view="trash") == []
    assert (await auth_client.post(f"/api/projects/{p['id']}/restore")).status_code == 404


# ------------------------------------------------------------------ star, views
async def test_star_and_views(auth_client: AsyncClient, session) -> None:
    fresh, old = await make(auth_client, "Fresh"), await make(auth_client, "Old")
    await auth_client.patch(f"/api/projects/{fresh['id']}", json={"starred": True})
    assert await titles(auth_client, view="starred") == ["Fresh"]
    await session.execute(
        update(Project)
        .where(Project.id == uuid.UUID(old["id"]))
        .values(updated_at=datetime.now(UTC) - timedelta(days=60))
    )
    await session.commit()
    assert await titles(auth_client, view="recent") == ["Fresh"]
    assert await titles(auth_client) == ["Fresh", "Old"]
    assert await titles(auth_client, q="fre") == ["Fresh"]
    r = await auth_client.get("/api/projects", params={"sort": "title"})
    assert [p["title"] for p in r.json()["items"]] == ["Fresh", "Old"]
    # starring is not a way to un-star by null
    await auth_client.patch(f"/api/projects/{fresh['id']}", json={"starred": None})
    assert await titles(auth_client, view="starred") == ["Fresh"]


# --------------------------------------------------------------------- folders
async def test_folders_group_projects(auth_client: AsyncClient) -> None:
    folder = (await auth_client.post("/api/folders", json={"name": "Travel films"})).json()
    a, b = await make(auth_client, "In folder"), await make(auth_client, "Loose")
    r = await auth_client.patch(f"/api/projects/{a['id']}", json={"folder_id": folder["id"]})
    assert r.json()["folder_id"] == folder["id"]
    assert await titles(auth_client, folder=folder["id"]) == ["In folder"]
    assert await titles(auth_client, folder="none") == ["Loose"]
    listed = (await auth_client.get("/api/folders")).json()
    assert [(f["name"], f["project_count"]) for f in listed] == [("Travel films", 1)]
    renamed = await auth_client.patch(f"/api/folders/{folder['id']}", json={"name": "Films"})
    assert renamed.json()["name"] == "Films"
    # deleting a folder keeps its projects
    assert (await auth_client.delete(f"/api/folders/{folder['id']}")).status_code == 204
    assert await titles(auth_client, folder="none") == ["In folder", "Loose"]
    # a project can be taken out of a folder with null
    f2 = (await auth_client.post("/api/folders", json={"name": "Two"})).json()
    await auth_client.patch(f"/api/projects/{b['id']}", json={"folder_id": f2["id"]})
    r = await auth_client.patch(f"/api/projects/{b['id']}", json={"folder_id": None})
    assert r.json()["folder_id"] is None


async def test_folders_are_private(auth_client: AsyncClient, client: AsyncClient) -> None:
    mine = (await auth_client.post("/api/folders", json={"name": "Mine"})).json()
    other = await client.post(
        "/api/auth/register",
        json={"email": f"o-{uuid.uuid4().hex[:6]}@example.com", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get("/api/folders", headers=headers)).json() == []
    assert (
        await client.patch(f"/api/folders/{mine['id']}", json={"name": "x"}, headers=headers)
    ).status_code == 404
    p = (await client.post("/api/projects", json={"title": "theirs"}, headers=headers)).json()
    r = await client.patch(
        f"/api/projects/{p['id']}", json={"folder_id": mine["id"]}, headers=headers
    )
    assert r.status_code == 404


# ------------------------------------------------------------------------ bulk
async def test_bulk_actions(auth_client: AsyncClient) -> None:
    a = await make(auth_client, "A")
    b = await make(auth_client, "B")
    c = await make(auth_client, "C")
    ids = [a["id"], b["id"]]
    r = await auth_client.post("/api/projects/bulk", json={"ids": ids, "action": "star"})
    assert r.json() == {"changed": 2}
    assert await titles(auth_client, view="starred") == ["A", "B"]
    await auth_client.post("/api/projects/bulk", json={"ids": ids, "action": "unstar"})
    assert await titles(auth_client, view="starred") == []

    folder = (await auth_client.post("/api/folders", json={"name": "F"})).json()
    await auth_client.post(
        "/api/projects/bulk", json={"ids": ids, "action": "move", "folder_id": folder["id"]}
    )
    assert await titles(auth_client, folder=folder["id"]) == ["A", "B"]

    dup = await auth_client.post("/api/projects/bulk", json={"ids": ids, "action": "duplicate"})
    assert dup.json()["changed"] == 2
    assert len(await titles(auth_client)) == 5

    await auth_client.post(
        "/api/projects/bulk", json={"ids": [a["id"], c["id"]], "action": "trash"}
    )
    assert "A" not in await titles(auth_client) and "C" not in await titles(auth_client)
    await auth_client.post("/api/projects/bulk", json={"ids": [a["id"]], "action": "restore"})
    assert "A" in await titles(auth_client)
    await auth_client.post("/api/projects/bulk", json={"ids": [c["id"]], "action": "delete"})
    assert await titles(auth_client, view="trash") == []


async def test_bulk_ignores_other_peoples_projects_and_bad_input(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    other = await client.post(
        "/api/auth/register",
        json={"email": f"o-{uuid.uuid4().hex[:6]}@example.com", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    theirs = (await client.post("/api/projects", json={"title": "theirs"}, headers=headers)).json()
    r = await auth_client.post(
        "/api/projects/bulk", json={"ids": [theirs["id"], str(uuid.uuid4())], "action": "trash"}
    )
    assert r.json() == {"changed": 0}
    assert (await client.get(f"/api/projects/{theirs['id']}", headers=headers)).status_code == 200
    bad = await auth_client.post(
        "/api/projects/bulk", json={"ids": [theirs["id"]], "action": "nuke"}
    )
    assert bad.status_code == 422
    empty = await auth_client.post("/api/projects/bulk", json={"ids": [], "action": "trash"})
    assert empty.status_code == 422


# ----------------------------------------------- storage, activity and templates
async def test_storage_reports_plan_limit(auth_client: AsyncClient) -> None:
    body = (await auth_client.get("/api/account/storage")).json()
    assert body["plan"] == "free"
    assert body["used_bytes"] == 0
    assert body["limit_bytes"] == 2048 * 1024 * 1024


async def test_activity_lists_new_projects(auth_client: AsyncClient) -> None:
    await make(auth_client, "Fresh idea")
    items = (await auth_client.get("/api/account/activity")).json()
    assert [(i["kind"], i["title"]) for i in items] == [("created", "Fresh idea")]


async def test_template_gallery(auth_client: AsyncClient) -> None:
    body = (await auth_client.get("/api/templates")).json()
    assert body["categories"] == ["social", "business", "education", "story"]
    assert len(body["templates"]) >= 9
    first = body["templates"][0]
    assert first["thumbnail_url"] == f"/templates/{first['key']}.jpg"
    assert {t["category"] for t in body["templates"]} == set(body["categories"])
    # what the web app needs to redraw a cover live on hover
    for t in body["templates"]:
        assert t["headline"] and t["kicker"]
        assert t["mood"] in {"hook", "setup", "rising", "twist", "climax", "payoff"}
    assert len({t["mood"] for t in body["templates"]}) > 1


# ------------------------------------------------------- create options (wizard)
async def test_create_with_hd_resolution_and_folder(auth_client: AsyncClient) -> None:
    folder = (await auth_client.post("/api/folders", json={"name": "Films"})).json()
    r = await auth_client.post(
        "/api/projects",
        json={
            "title": "Wizard",
            "aspect_ratio": "16:9",
            "resolution": "hd",
            "fps": 24,
            "folder_id": folder["id"],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert (body["width"], body["height"], body["fps"]) == (1280, 720, 24)
    assert body["folder_id"] == folder["id"]
    # the shape stays right in portrait, and full HD is the default
    portrait = (
        await auth_client.post(
            "/api/projects", json={"title": "P", "aspect_ratio": "9:16", "resolution": "hd"}
        )
    ).json()
    assert (portrait["width"], portrait["height"]) == (720, 1280)
    default = (await auth_client.post("/api/projects", json={"title": "D"})).json()
    assert (default["width"], default["height"]) == (1080, 1920)
    up = await auth_client.patch(f"/api/projects/{default['id']}", json={"resolution": "hd"})
    assert (up.json()["width"], up.json()["height"]) == (720, 1280)


async def test_create_in_someone_elses_folder_is_refused(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    other = await client.post(
        "/api/auth/register",
        json={"email": f"o-{uuid.uuid4().hex[:6]}@example.com", "password": PASSWORD},
    )
    headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    theirs = (await client.post("/api/folders", json={"name": "T"}, headers=headers)).json()
    r = await auth_client.post("/api/projects", json={"title": "x", "folder_id": theirs["id"]})
    assert r.status_code == 404
