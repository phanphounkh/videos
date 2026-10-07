"""Authentication and authorization."""

import uuid

from httpx import AsyncClient

from app.core.security import hash_password, verify_password


def test_password_hash_is_not_reversible() -> None:
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert verify_password("supersecret123", hashed)
    assert not verify_password("wrong", hashed)


def test_corrupt_hash_fails_closed() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


async def test_register_then_me(client: AsyncClient) -> None:
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    created = await client.post(
        "/api/auth/register", json={"email": email, "password": "supersecret123"}
    )
    assert created.status_code == 201
    token = created.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_duplicate_email_is_rejected(client: AsyncClient) -> None:
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    body = {"email": email, "password": "supersecret123"}
    assert (await client.post("/api/auth/register", json=body)).status_code == 201
    conflict = await client.post("/api/auth/register", json=body)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_login_with_wrong_password_is_generic(client: AsyncClient) -> None:
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/auth/register", json={"email": email, "password": "supersecret123"})

    wrong = await client.post("/api/auth/login", json={"email": email, "password": "nope12345"})
    missing = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "nope12345"}
    )
    # Identical response: the login form must not reveal which emails exist.
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


async def test_short_password_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register", json={"email": "x@example.com", "password": "short"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_protected_routes_require_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/projects")).status_code == 401
    assert (
        await client.get("/api/projects", headers={"Authorization": "Bearer garbage"})
    ).status_code == 401
