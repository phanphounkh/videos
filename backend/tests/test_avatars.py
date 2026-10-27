"""Selectable hosts: the catalogue, uploaded photos, favourites, per-project choice,
resolution rules and the renderer payloads."""

import io
import uuid

import pytest
from httpx import AsyncClient
from PIL import Image

from app.repositories.project_repository import ProjectRepository
from app.services.avatars import avatar_spec, resolve_avatar
from app.services.render_payload import build_composition_payload
from app.services.storage import get_storage
from app.services.thumbnail_service import thumbnail_payload

from .test_accounts import bearer, register

EXPECTED = {
    "toon-m-young": ("Dara", "toon", "male", "young"),
    "toon-f-young": ("Sophea", "toon", "female", "young"),
    "toon-m-adult": ("Vuthy", "toon", "male", "adult"),
    "toon-f-adult": ("Chenda", "toon", "female", "adult"),
    "toon-m-old": ("Ta Sok", "toon", "male", "old"),
    "toon-f-old": ("Yeay Sarun", "toon", "female", "old"),
    "real-m-young": ("Rithy", "real", "male", "young"),
    "real-f-young": ("Maly", "real", "female", "young"),
    "real-m-adult": ("Samnang", "real", "male", "adult"),
    "real-f-adult": ("Bopha", "real", "female", "adult"),
    "real-m-old": ("Lok Sen", "real", "male", "old"),
    "real-f-old": ("Daun Pen", "real", "female", "old"),
}


def _png(width: int = 800, height: int = 300, mode: str = "RGB", color=(30, 120, 220)) -> bytes:
    out = io.BytesIO()
    Image.new(mode, (width, height), color).save(out, format="PNG")
    return out.getvalue()


async def upload(client: AsyncClient, person: dict, name: str | None = None, **data) -> dict:
    if name is not None:
        data["name"] = name
    r = await client.post(
        "/api/avatars",
        files={"file": ("me.png", _png(), "image/png")},
        data=data,
        headers=bearer(person),
    )
    assert r.status_code == 201, r.text
    return r.json()


def key_of(url: str) -> str:
    return url.split("/", 4)[-1].replace("%2F", "/")


# -------------------------------------------------------------------- catalogue
async def test_catalogue_lists_the_twelve_builtin_hosts(client: AsyncClient) -> None:
    me = await register(client, "cat")
    r = await client.get("/api/avatars", headers=bearer(me))
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["builtin"]) == 12
    got = {a["id"]: a for a in body["builtin"]}
    assert set(got) == set(EXPECTED)
    for avatar_id, (name, style, gender, age) in EXPECTED.items():
        assert got[avatar_id] == {
            "id": avatar_id,
            "name": name,
            "style": style,
            "gender": gender,
            "age": age,
            "preview_url": f"/avatars/{avatar_id}.png",
        }
    assert body["custom"] == []
    assert body["preferences"] == {"default": None, "auto": True}


async def test_catalogue_needs_a_sign_in(client: AsyncClient) -> None:
    assert (await client.get("/api/avatars")).status_code == 401


# ----------------------------------------------------------------------- upload
async def test_upload_is_cropped_to_a_512_jpeg(client: AsyncClient) -> None:
    me = await register(client, "up")
    item = await upload(client, me)
    assert item["id"].startswith("custom:") and item["name"] == "My avatar"
    assert item["mode"] == "mouth"
    assert f"avatar-photos/{me['id']}/" in item["image_url"]
    stored = Image.open(io.BytesIO(await get_storage().get_bytes(key_of(item["image_url"]))))
    assert stored.size == (512, 512) and stored.format == "JPEG"
    listed = (await client.get("/api/avatars", headers=bearer(me))).json()["custom"]
    assert listed == [item]


async def test_upload_name_and_mode_and_transparency(client: AsyncClient) -> None:
    me = await register(client, "named")
    r = await client.post(
        "/api/avatars",
        files={"file": ("t.png", _png(100, 100, "RGBA", (0, 0, 0, 0)), "image/png")},
        data={"name": "Grandpa", "mode": "subtle"},
        headers=bearer(me),
    )
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["name"] == "Grandpa" and item["mode"] == "subtle"
    stored = Image.open(io.BytesIO(await get_storage().get_bytes(key_of(item["image_url"]))))
    assert min(stored.getpixel((10, 10))) > 240  # flattened onto white, not black
    bad = await client.post(
        "/api/avatars",
        files={"file": ("t.png", _png(), "image/png")},
        data={"mode": "weird"},
        headers=bearer(me),
    )
    assert bad.status_code == 422


async def test_upload_rejects_non_images_and_big_files(client: AsyncClient) -> None:
    me = await register(client, "bad")
    r = await client.post(
        "/api/avatars",
        files={"file": ("x.png", b"definitely not an image", "image/png")},
        headers=bearer(me),
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_IMAGE"
    r = await client.post(
        "/api/avatars",
        files={"file": ("big.png", b"0" * (8 * 1024 * 1024 + 10), "image/png")},
        headers=bearer(me),
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert (await client.get("/api/avatars", headers=bearer(me))).json()["custom"] == []


async def test_upload_limit_is_twelve(client: AsyncClient) -> None:
    me = await register(client, "many")
    for i in range(12):
        await upload(client, me, f"A{i}")
    r = await client.post(
        "/api/avatars", files={"file": ("x.png", _png(), "image/png")}, headers=bearer(me)
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "AVATAR_LIMIT"
    # the limit is per person
    other = await register(client, "other")
    await upload(client, other)


# ------------------------------------------------------------ patch and delete
async def test_patch_renames_and_changes_mode(client: AsyncClient) -> None:
    me = await register(client, "patch")
    item = await upload(client, me)
    uid = item["id"].split(":", 1)[1]
    r = await client.patch(
        f"/api/avatars/{uid}", json={"name": "Boss", "mode": "subtle"}, headers=bearer(me)
    )
    assert r.status_code == 200, r.text
    assert r.json() == {**item, "name": "Boss", "mode": "subtle"}
    r = await client.patch(f"/api/avatars/{uid}", json={"mode": "nope"}, headers=bearer(me))
    assert r.status_code == 422


async def test_other_peoples_avatars_are_not_found(client: AsyncClient) -> None:
    owner, intruder = await register(client, "own"), await register(client, "snoop")
    uid = (await upload(client, owner))["id"].split(":", 1)[1]
    assert (
        await client.patch(f"/api/avatars/{uid}", json={"name": "x"}, headers=bearer(intruder))
    ).status_code == 404
    assert (await client.delete(f"/api/avatars/{uid}", headers=bearer(intruder))).status_code == 404
    assert (
        await client.delete(f"/api/avatars/{uuid.uuid4()}", headers=bearer(owner))
    ).status_code == 404
    assert len((await client.get("/api/avatars", headers=bearer(owner))).json()["custom"]) == 1


async def test_delete_removes_the_file_and_resets_projects(client: AsyncClient) -> None:
    me = await register(client, "del")
    item = await upload(client, me)
    uid = item["id"].split(":", 1)[1]
    key = key_of(item["image_url"])
    project = (
        await client.post(
            "/api/projects", json={"title": "Mine", "avatar": item["id"]}, headers=bearer(me)
        )
    ).json()
    keeper = (
        await client.post(
            "/api/projects", json={"title": "Keeps", "avatar": "toon-f-old"}, headers=bearer(me)
        )
    ).json()
    await client.put(
        "/api/account/avatar-preferences",
        json={"default": item["id"], "auto": True},
        headers=bearer(me),
    )
    assert await get_storage().exists(key)

    assert (await client.delete(f"/api/avatars/{uid}", headers=bearer(me))).status_code == 204
    assert not await get_storage().exists(key)
    after = (await client.get(f"/api/projects/{project['id']}", headers=bearer(me))).json()
    assert after["avatar"] is None and after["avatar_resolved"] == "toon-m-young"
    other = (await client.get(f"/api/projects/{keeper['id']}", headers=bearer(me))).json()
    assert other["avatar"] == "toon-f-old"
    cat = (await client.get("/api/avatars", headers=bearer(me))).json()
    assert cat["custom"] == [] and cat["preferences"]["default"] is None


# ------------------------------------------------------------------ preferences
async def test_preferences_round_trip_and_validation(client: AsyncClient) -> None:
    me, other = await register(client, "pref"), await register(client, "pref2")
    r = await client.put(
        "/api/account/avatar-preferences",
        json={"default": "real-f-young", "auto": False},
        headers=bearer(me),
    )
    assert r.status_code == 200 and r.json() == {"default": "real-f-young", "auto": False}
    cat = (await client.get("/api/avatars", headers=bearer(me))).json()
    assert cat["preferences"] == {"default": "real-f-young", "auto": False}

    mine = (await upload(client, me))["id"]
    r = await client.put(
        "/api/account/avatar-preferences", json={"default": mine, "auto": True}, headers=bearer(me)
    )
    assert r.status_code == 200 and r.json()["default"] == mine

    theirs = (await upload(client, other))["id"]
    for bad in ("nope", "toon-x-young", theirs, f"custom:{uuid.uuid4()}", "custom:zzz"):
        r = await client.put(
            "/api/account/avatar-preferences",
            json={"default": bad, "auto": True},
            headers=bearer(me),
        )
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "INVALID_AVATAR"
    r = await client.put(
        "/api/account/avatar-preferences", json={"default": None, "auto": True}, headers=bearer(me)
    )
    assert r.json() == {"default": None, "auto": True}


# --------------------------------------------------------------------- projects
async def test_project_avatar_create_update_and_validation(client: AsyncClient) -> None:
    me, other = await register(client, "proj"), await register(client, "proj2")
    r = await client.post(
        "/api/projects", json={"title": "A", "avatar": "real-m-old"}, headers=bearer(me)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["avatar"] == "real-m-old" and body["avatar_resolved"] == "real-m-old"
    pid = body["id"]

    mine = (await upload(client, me))["id"]
    r = await client.patch(f"/api/projects/{pid}", json={"avatar": mine}, headers=bearer(me))
    assert r.status_code == 200 and r.json()["avatar_resolved"] == mine
    # a PATCH that omits it leaves it alone
    r = await client.patch(f"/api/projects/{pid}", json={"title": "B"}, headers=bearer(me))
    assert r.json()["avatar"] == mine
    # explicit null goes back to automatic
    r = await client.patch(f"/api/projects/{pid}", json={"avatar": None}, headers=bearer(me))
    assert r.json()["avatar"] is None and r.json()["avatar_resolved"] == "toon-m-young"

    theirs = (await upload(client, other))["id"]
    for bad in ("bogus", theirs):
        r = await client.patch(f"/api/projects/{pid}", json={"avatar": bad}, headers=bearer(me))
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_AVATAR"
        r = await client.post(
            "/api/projects", json={"title": "C", "avatar": bad}, headers=bearer(me)
        )
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_AVATAR"


async def test_duplicate_keeps_the_avatar(client: AsyncClient) -> None:
    me = await register(client, "dup")
    p = (
        await client.post(
            "/api/projects", json={"title": "A", "avatar": "toon-f-adult"}, headers=bearer(me)
        )
    ).json()
    r = await client.post(f"/api/projects/{p['id']}/duplicate", headers=bearer(me))
    assert r.status_code == 201 and r.json()["avatar"] == "toon-f-adult"


# ------------------------------------------------------------ resolution rules
class _User:
    def __init__(self, default: str | None, auto: bool) -> None:
        self.avatar_default = default
        self.avatar_auto = auto


CUSTOM = f"custom:{uuid.uuid4()}"


@pytest.mark.parametrize(
    ("project_avatar", "default", "auto", "purpose", "expected"),
    [
        # 1) the project's own choice wins over everything
        ("real-m-old", "toon-f-young", True, "story", "real-m-old"),
        (CUSTOM, "toon-f-young", False, "explainer", CUSTOM),
        # 2) favourite: custom is always used as is
        (None, CUSTOM, True, "story", CUSTOM),
        (None, CUSTOM, False, "product_demo", CUSTOM),
        # built-in with auto off: used as is
        (None, "real-f-young", False, "story", "real-f-young"),
        (None, "toon-m-old", False, "explainer", "toon-m-old"),
        # built-in with auto on: same person, style suited to the purpose
        (None, "real-f-young", True, "story", "toon-f-young"),
        (None, "real-m-old", True, "social_post", "toon-m-old"),
        (None, "real-f-adult", True, "creator", "toon-f-adult"),
        (None, "toon-f-young", True, "product_demo", "real-f-young"),
        (None, "toon-m-old", True, "explainer", "real-m-old"),
        (None, "toon-m-young", True, "story", "toon-m-young"),
        # 3) purpose defaults
        (None, None, True, "story", "toon-m-young"),
        (None, None, True, "social_post", "toon-f-young"),
        (None, None, True, "creator", "toon-m-adult"),
        (None, None, True, "product_demo", "real-f-adult"),
        (None, None, False, "explainer", "real-m-adult"),
    ],
)
def test_resolve_avatar_rules(project_avatar, default, auto, purpose, expected) -> None:
    assert resolve_avatar(project_avatar, _User(default, auto), purpose) == expected  # type: ignore[arg-type]


async def test_avatar_resolved_in_the_api_follows_the_favourite(client: AsyncClient) -> None:
    me = await register(client, "res")
    await client.put(
        "/api/account/avatar-preferences",
        json={"default": "real-f-young", "auto": True},
        headers=bearer(me),
    )
    story = (
        await client.post(
            "/api/projects", json={"title": "S", "purpose": "story"}, headers=bearer(me)
        )
    ).json()
    demo = (
        await client.post(
            "/api/projects", json={"title": "D", "purpose": "product_demo"}, headers=bearer(me)
        )
    ).json()
    assert story["avatar"] is None and story["avatar_resolved"] == "toon-f-young"
    assert demo["avatar_resolved"] == "real-f-young"
    # changing the preference is reflected in the list too
    await client.put(
        "/api/account/avatar-preferences",
        json={"default": "real-f-young", "auto": False},
        headers=bearer(me),
    )
    items = (await client.get("/api/projects", headers=bearer(me))).json()["items"]
    assert {p["avatar_resolved"] for p in items} == {"real-f-young"}


# --------------------------------------------------------------------- payloads
async def _load(client: AsyncClient, session, person: dict, **fields):
    created = (
        await client.post("/api/projects", json={"title": "P", **fields}, headers=bearer(person))
    ).json()
    project = await ProjectRepository(session).get_for_owner(
        uuid.UUID(created["id"]), uuid.UUID(person["id"])
    )
    assert project is not None
    return project


async def test_payloads_carry_a_builtin_avatar(client: AsyncClient, session) -> None:
    me = await register(client, "pay")
    project = await _load(client, session, me, presenter=True, avatar="real-f-old")
    expected = {"kind": "builtin", "id": "real-f-old", "imageUrl": None, "mode": "mouth"}
    assert build_composition_payload(project)["project"]["avatar"] == expected
    assert thumbnail_payload(project)["project"]["avatar"] == expected
    spec = await avatar_spec(session, project)
    assert spec == expected


async def test_payloads_carry_a_custom_avatar(client: AsyncClient, session) -> None:
    me = await register(client, "pay2")
    item = await upload(client, me, mode="subtle")
    project = await _load(client, session, me, presenter=True, avatar=item["id"])
    spec = await avatar_spec(session, project)
    assert spec["kind"] == "photo" and spec["id"] == item["id"] and spec["mode"] == "subtle"
    assert spec["imageUrl"].endswith(key_of(item["image_url"]).replace("/", "%2F")) or (
        key_of(item["image_url"]) in spec["imageUrl"].replace("%2F", "/")
    )
    assert build_composition_payload(project, spec)["project"]["avatar"] == spec
    assert thumbnail_payload(project, spec)["project"]["avatar"] == spec


async def test_payload_uses_the_favourite_and_purpose(client: AsyncClient, session) -> None:
    me = await register(client, "pay3")
    await client.put(
        "/api/account/avatar-preferences",
        json={"default": "toon-m-old", "auto": True},
        headers=bearer(me),
    )
    project = await _load(client, session, me, presenter=True, purpose="explainer")
    assert build_composition_payload(project)["project"]["avatar"]["id"] == "real-m-old"


async def test_no_host_means_no_avatar_in_the_payloads(client: AsyncClient, session) -> None:
    me = await register(client, "nohost")
    project = await _load(client, session, me, presenter=False, avatar="toon-m-adult")
    assert "avatar" not in build_composition_payload(project)["project"]
    assert "avatar" not in thumbnail_payload(project)["project"]
