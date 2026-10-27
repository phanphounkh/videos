"""Test harness: a throwaway Postgres database (real migrations) and a real Redis stream.

Like the backend's tests, these run against the real thing: the schema uses JSONB, a
partial index and an identity column, and a fake would test a different database than
the one that ships. Only the BACKEND is faked (who is an admin, whose email is whose).
"""

import asyncio
import os
import subprocess
import uuid
from pathlib import Path

import pytest
import redis.asyncio as redis
from asyncpg import connect

BASE = os.environ.get("TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@localhost:5437")
TEST_DB = f"telemetry_test_{uuid.uuid4().hex[:8]}"
from tests.helpers import SECRET, token_for  # noqa: E402

# Set BEFORE any app module is imported: the engine reads its URL once, at import.
os.environ["DATABASE_URL"] = f"postgresql+asyncpg://postgres:postgres@localhost:5437/{TEST_DB}"
os.environ["JWT_SECRET"] = SECRET
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6381/15")
os.environ["RETENTION_ENABLED"] = "false"

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def database():
    async def run(sql: str) -> None:
        conn = await connect(f"{BASE}/postgres")
        try:
            await conn.execute(sql)
        finally:
            await conn.close()

    asyncio.run(run(f'CREATE DATABASE "{TEST_DB}"'))
    # The real migrations: a broken one fails the suite here.
    migrated = subprocess.run(
        ["alembic", "upgrade", "head"], cwd=ROOT, env={**os.environ}, capture_output=True, text=True
    )
    assert migrated.returncode == 0, f"alembic failed:\n{migrated.stderr[-1500:]}"
    yield
    asyncio.run(run(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))


@pytest.fixture(autouse=True)
async def _clean_between_tests():
    """Each test starts with an empty table, and leaves no pooled connection behind:
    pytest gives every test its own event loop, and a connection belongs to the loop
    that opened it."""
    from sqlalchemy import text

    from app import ratelimit
    from app.database import SessionLocal, engine
    from auth import backend

    async with SessionLocal() as db:
        await db.execute(text("TRUNCATE events RESTART IDENTITY"))
        await db.commit()
    backend.reset_caches()
    ratelimit.reset()
    yield
    await engine.dispose()


@pytest.fixture
async def stream(monkeypatch):
    """A private Redis stream and consumer group for one test."""
    from app.config import get_settings

    settings = get_settings()
    key = f"test:telemetry:{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(settings, "telemetry_stream_key", key)
    monkeypatch.setattr(settings, "telemetry_consumer_group", f"g-{uuid.uuid4().hex[:6]}")
    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    yield r
    await r.delete(key)
    async for k in r.scan_iter("telemetry:ratelimit:*"):
        await r.delete(k)
    await r.aclose()


@pytest.fixture
def admin_token(monkeypatch) -> str:
    """A valid token the (faked) backend says belongs to an admin."""
    from auth import backend

    token = token_for("admin-1")

    async def is_admin(t: str) -> bool:
        return t == token

    async def emails(t: str, ids: list[str]) -> dict:
        return {i: f"{i}@example.test" for i in ids}

    monkeypatch.setattr(backend, "is_admin", is_admin)
    monkeypatch.setattr(backend, "emails", emails)
    return token


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
