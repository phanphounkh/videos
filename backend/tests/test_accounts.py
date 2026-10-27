"""The signed-in person's account, the admin's control over people, and monthly limits."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.user import User
from app.services import usage

PASSWORD = "supersecret123"


async def register(client: AsyncClient, name: str) -> dict:
    email = f"{name}-{uuid.uuid4().hex[:6]}@example.com"
    response = await client.post(
        "/api/auth/register", json={"email": email, "password": PASSWORD, "full_name": name}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {"id": body["user"]["id"], "email": email, "token": body["access_token"]}


def bearer(person: dict) -> dict:
    return {"Authorization": f"Bearer {person['token']}"}


@pytest.fixture
async def admin(client: AsyncClient, session) -> dict:
    person = await register(client, "boss")
    await session.execute(
        update(User).where(User.id == uuid.UUID(person["id"])).values(is_admin=True)
    )
    await session.commit()
    return person


# ------------------------------------------------------------------ own account
async def test_profile_and_password(client: AsyncClient) -> None:
    me = await register(client, "ada")
    r = await client.patch(
        "/api/account/profile", json={"full_name": " Ada L "}, headers=bearer(me)
    )
    assert r.status_code == 200 and r.json()["full_name"] == "Ada L"

    bad = await client.post(
        "/api/account/password",
        json={"current_password": "nope-nope", "new_password": "another-pass-1"},
        headers=bearer(me),
    )
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "WRONG_PASSWORD"
    ok = await client.post(
        "/api/account/password",
        json={"current_password": PASSWORD, "new_password": "another-pass-1"},
        headers=bearer(me),
    )
    assert ok.status_code == 200
    login = await client.post(
        "/api/auth/login", json={"email": me["email"], "password": "another-pass-1"}
    )
    assert login.status_code == 200


async def test_usage_reports_plan_and_counts(client: AsyncClient) -> None:
    me = await register(client, "uma")
    await usage.add(me["id"], "ai_calls", 3)
    body = (await client.get("/api/account/usage", headers=bearer(me))).json()
    assert body["plan"] == "free"
    assert body["used"]["ai_calls"] == 3 and body["limits"]["ai_calls"] is None
    await usage.reset(me["id"])


async def test_delete_account_needs_the_password(client: AsyncClient) -> None:
    me = await register(client, "gone")
    wrong = await client.request(
        "DELETE", "/api/account", json={"password": "wrong-pass"}, headers=bearer(me)
    )
    assert wrong.status_code == 401
    done = await client.request(
        "DELETE", "/api/account", json={"password": PASSWORD}, headers=bearer(me)
    )
    assert done.status_code == 204
    assert (await client.get("/api/auth/me", headers=bearer(me))).status_code == 401


# ------------------------------------------------------------------- admin area
async def test_admin_area_refuses_ordinary_users(client: AsyncClient) -> None:
    me = await register(client, "plain")
    for path in ("/api/admin/users", "/api/admin/stats", f"/api/admin/users/{me['id']}"):
        assert (await client.get(path, headers=bearer(me))).status_code == 403
    assert (await client.get("/api/admin/users")).status_code == 401


async def test_list_search_and_filter(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "needle")
    r = await client.get("/api/admin/users", params={"q": "needle"}, headers=bearer(admin))
    assert r.status_code == 200
    assert [u["email"] for u in r.json()["items"]] == [other["email"]]
    admins = await client.get("/api/admin/users", params={"status": "admin"}, headers=bearer(admin))
    assert all(u["is_admin"] for u in admins.json()["items"])


async def test_detail_includes_projects(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "maker")
    await client.post("/api/projects", json={"title": "Reel"}, headers=bearer(other))
    body = (await client.get(f"/api/admin/users/{other['id']}", headers=bearer(admin))).json()
    assert body["user"]["project_count"] == 1
    assert body["recent_projects"][0]["title"] == "Reel"


async def test_disable_blocks_access_and_enable_restores(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "target")
    r = await client.patch(
        f"/api/admin/users/{other['id']}", json={"is_active": False}, headers=bearer(admin)
    )
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert (await client.get("/api/auth/me", headers=bearer(other))).status_code == 403
    login = await client.post(
        "/api/auth/login", json={"email": other["email"], "password": PASSWORD}
    )
    assert login.json()["error"]["code"] == "ACCOUNT_DISABLED"
    await client.patch(
        f"/api/admin/users/{other['id']}", json={"is_active": True}, headers=bearer(admin)
    )
    assert (await client.get("/api/auth/me", headers=bearer(other))).status_code == 200


async def test_admin_cannot_lock_themselves_out(client: AsyncClient, admin: dict) -> None:
    for body in ({"is_active": False}, {"is_admin": False}):
        r = await client.patch(f"/api/admin/users/{admin['id']}", json=body, headers=bearer(admin))
        assert r.status_code == 409 and r.json()["error"]["code"] == "CANNOT_CHANGE_SELF"
    r = await client.delete(f"/api/admin/users/{admin['id']}", headers=bearer(admin))
    assert r.status_code == 409


async def test_grant_and_revoke_admin(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "deputy")
    r = await client.patch(
        f"/api/admin/users/{other['id']}", json={"is_admin": True}, headers=bearer(admin)
    )
    assert r.json()["is_admin"] is True
    assert (await client.get("/api/admin/stats", headers=bearer(other))).status_code == 200
    r = await client.patch(
        f"/api/admin/users/{other['id']}", json={"is_admin": False}, headers=bearer(admin)
    )
    assert r.json()["is_admin"] is False


async def test_last_admin_is_protected(client: AsyncClient, admin: dict, session) -> None:
    # Make every OTHER admin non-admin, then try to demote the sole remaining one via a
    # second admin who is then the only other: the guard counts active admins.
    second = await register(client, "second")
    await client.patch(
        f"/api/admin/users/{second['id']}", json={"is_admin": True}, headers=bearer(admin)
    )
    await client.patch(
        f"/api/admin/users/{admin['id']}", json={"is_active": True}, headers=bearer(second)
    )
    # second disables first: allowed, second remains
    ok = await client.patch(
        f"/api/admin/users/{admin['id']}", json={"is_admin": False}, headers=bearer(second)
    )
    assert ok.status_code == 200
    # now second is the only admin among those it could target besides itself: self-guard
    r = await client.patch(
        f"/api/admin/users/{second['id']}", json={"is_admin": False}, headers=bearer(second)
    )
    assert r.status_code == 409


async def test_unsent_limit_is_left_alone_and_null_means_unlimited(
    client: AsyncClient, admin: dict
) -> None:
    other = await register(client, "capped")
    url = f"/api/admin/users/{other['id']}"
    r = await client.patch(
        url, json={"plan": "pro", "limit_exports": 5, "limit_ai_calls": 10}, headers=bearer(admin)
    )
    assert (r.json()["plan"], r.json()["limit_exports"]) == ("pro", 5)
    r = await client.patch(url, json={"limit_exports": None}, headers=bearer(admin))
    assert r.json()["limit_exports"] is None and r.json()["limit_ai_calls"] == 10
    r = await client.patch(url, json={"plan": "Bad Plan!"}, headers=bearer(admin))
    assert r.status_code == 422


async def test_delete_user(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "victim")
    assert (
        await client.delete(f"/api/admin/users/{other['id']}", headers=bearer(admin))
    ).status_code == 204
    assert (
        await client.get(f"/api/admin/users/{other['id']}", headers=bearer(admin))
    ).status_code == 404


async def test_lookup_returns_emails(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "findme")
    r = await client.get(
        "/api/admin/users/lookup",
        params={"ids": f"{other['id']},not-a-uuid,{uuid.uuid4()}"},
        headers=bearer(admin),
    )
    assert r.json() == {other["id"]: other["email"]}


# ------------------------------------------------------------------------ limits
async def test_export_limit_is_enforced(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "limited")
    await client.patch(
        f"/api/admin/users/{other['id']}", json={"limit_exports": 1}, headers=bearer(admin)
    )
    project = (
        await client.post("/api/projects", json={"title": "x"}, headers=bearer(other))
    ).json()
    await usage.add(other["id"], "exports", 1)
    r = await client.post(f"/api/projects/{project['id']}/render", headers=bearer(other))
    assert r.status_code == 429
    body = r.json()["error"]
    assert body["code"] == "QUOTA_EXCEEDED"
    assert body["details"]["limit"] == 1
    # an admin can reset the month and the person can go on
    await client.post(f"/api/admin/users/{other['id']}/reset-usage", headers=bearer(admin))
    r = await client.post(f"/api/projects/{project['id']}/render", headers=bearer(other))
    assert r.status_code != 429
    await usage.reset(other["id"])


async def test_ai_limit_blocks_generation(client: AsyncClient, admin: dict) -> None:
    other = await register(client, "aicap")
    await client.patch(
        f"/api/admin/users/{other['id']}", json={"limit_ai_calls": 0}, headers=bearer(admin)
    )
    project = (
        await client.post("/api/projects", json={"title": "x"}, headers=bearer(other))
    ).json()
    r = await client.post(
        f"/api/projects/{project['id']}/generate",
        json={"prompt": "a cat on a skateboard", "duration": 30},
        headers=bearer(other),
    )
    assert r.status_code == 429 and r.json()["error"]["code"] == "QUOTA_EXCEEDED"


async def test_bulk_delete_skips_self_and_reports_it(client: AsyncClient, admin: dict) -> None:
    a = await register(client, "bulk1")
    b = await register(client, "bulk2")
    r = await client.post(
        "/api/admin/users/bulk-delete",
        json={"ids": [a["id"], b["id"], admin["id"]]},
        headers=bearer(admin),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 2
    assert [s["id"] for s in body["skipped"]] == [admin["id"]]
    for gone in (a, b):
        assert (
            await client.get(f"/api/admin/users/{gone['id']}", headers=bearer(admin))
        ).status_code == 404
    assert (await client.get("/api/auth/me", headers=bearer(admin))).status_code == 200


async def test_bulk_delete_needs_admin_and_ids(client: AsyncClient, admin: dict) -> None:
    plain = await register(client, "bulkplain")
    r = await client.post(
        "/api/admin/users/bulk-delete", json={"ids": [plain["id"]]}, headers=bearer(plain)
    )
    assert r.status_code == 403
    r = await client.post("/api/admin/users/bulk-delete", json={"ids": []}, headers=bearer(admin))
    assert r.status_code == 422


# ----------------------------------------------------------------- profile picture
def _png(width: int, height: int, color=(30, 120, 220), mode: str = "RGB") -> bytes:
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new(mode, (width, height), color).save(out, format="PNG")
    return out.getvalue()


async def test_avatar_is_cropped_to_a_square_and_served(client: AsyncClient) -> None:
    import io

    from PIL import Image

    from app.services.storage import get_storage

    me = await register(client, "pic")
    assert (await client.get("/api/auth/me", headers=bearer(me))).json()["avatar_url"] is None
    r = await client.post(
        "/api/account/avatar",
        files={"file": ("me.png", _png(800, 300), "image/png")},
        headers=bearer(me),
    )
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert url and f"avatars/{me['id']}/" in url
    # it is persisted on the account and shows up everywhere the user does
    assert (await client.get("/api/auth/me", headers=bearer(me))).json()["avatar_url"] == url
    key = url.split("/", 4)[-1]
    stored = Image.open(io.BytesIO(await get_storage().get_bytes(key.replace("%2F", "/"))))
    assert stored.size == (256, 256) and stored.format == "JPEG"


async def test_replacing_and_removing_the_avatar(client: AsyncClient) -> None:
    from app.services.storage import get_storage

    me = await register(client, "swap")
    first = (
        await client.post(
            "/api/account/avatar",
            files={"file": ("a.png", _png(64, 64), "image/png")},
            headers=bearer(me),
        )
    ).json()["avatar_url"]
    second = (
        await client.post(
            "/api/account/avatar",
            files={"file": ("b.png", _png(64, 64, (200, 50, 50)), "image/png")},
            headers=bearer(me),
        )
    ).json()["avatar_url"]
    assert first != second  # a new address, so browsers do not show the old picture
    old_key = first.split("/", 4)[-1]
    assert not await get_storage().exists(old_key)  # the old file is cleaned up
    gone = await client.delete("/api/account/avatar", headers=bearer(me))
    assert gone.status_code == 200 and gone.json()["avatar_url"] is None


async def test_avatar_rejects_non_pictures_and_huge_files(client: AsyncClient) -> None:
    me = await register(client, "bad")
    not_image = await client.post(
        "/api/account/avatar",
        files={"file": ("x.png", b"definitely not an image", "image/png")},
        headers=bearer(me),
    )
    assert not_image.status_code == 422 and not_image.json()["error"]["code"] == "INVALID_IMAGE"
    huge = await client.post(
        "/api/account/avatar",
        files={"file": ("big.png", b"0" * (5 * 1024 * 1024 + 10), "image/png")},
        headers=bearer(me),
    )
    assert huge.status_code == 422 and huge.json()["error"]["code"] == "FILE_TOO_LARGE"
    empty = await client.post(
        "/api/account/avatar", files={"file": ("e.png", b"", "image/png")}, headers=bearer(me)
    )
    assert empty.status_code == 422
    assert (
        await client.post("/api/account/avatar", files={"file": ("a.png", _png(8, 8), "image/png")})
    ).status_code == 401


async def test_transparent_png_is_flattened_not_black(client: AsyncClient) -> None:
    import io

    from PIL import Image

    from app.services.storage import get_storage

    me = await register(client, "alpha")
    url = (
        await client.post(
            "/api/account/avatar",
            files={"file": ("t.png", _png(40, 40, (0, 0, 0, 0), "RGBA"), "image/png")},
            headers=bearer(me),
        )
    ).json()["avatar_url"]
    pixel = Image.open(io.BytesIO(await get_storage().get_bytes(url.split("/", 4)[-1]))).getpixel(
        (5, 5)
    )
    assert min(pixel) > 240  # white, not black
