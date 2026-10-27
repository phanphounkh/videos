"""Shared pytest fixtures.

Design decisions that matter:

  - Tests talk to a REAL PostgreSQL (the dockerised one), not SQLite. The schema
    uses JSONB and UUID columns, so SQLite would test a different database than
    the one we ship.
  - Each test session creates a throwaway database, runs the real Alembic
    migrations into it, and drops it afterwards. That also proves the migrations
    themselves work on every test run.
  - AI providers are replaced with in-memory fakes through the provider
    interfaces, so tests never hit the network, never cost money, and are fast.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def _admin_url(url: str) -> str:
    """Connection URL for the maintenance database (CREATE/DROP DATABASE)."""
    return url.rsplit("/", 1)[0] + "/postgres"


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[1]


@pytest.fixture(scope="session")
def test_database_url() -> str:
    base = get_settings().database_url
    return base.rsplit("/", 1)[0] + f"/avs_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session", autouse=True)
def database(test_database_url: str) -> AsyncIterator[str]:
    """Creates the test database, migrates it, and drops it at the end."""
    import subprocess
    from pathlib import Path

    from sqlalchemy import text

    async def create() -> None:
        engine = create_async_engine(_admin_url(test_database_url), isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            await conn.execute(text(f'CREATE DATABASE "{_database_name(test_database_url)}"'))
        await engine.dispose()

    async def drop() -> None:
        engine = create_async_engine(_admin_url(test_database_url), isolation_level="AUTOCOMMIT")
        name = _database_name(test_database_url)
        async with engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await engine.dispose()

    asyncio.run(create())

    # Run the real migrations: if a migration is broken, the suite fails here.
    env = {**os.environ, "DATABASE_URL": test_database_url}
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        check=True,
        capture_output=True,
    )

    # Point the application at the test database for the whole session, and
    # force offline providers so no test can reach the network or spend a
    # real API quota (a developer's .env may hold live keys).
    os.environ["DATABASE_URL"] = test_database_url
    os.environ["TTS_PROVIDER"] = "mock"
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["GEMINI_API_KEY"] = ""
    # Usage counters in Redis db 15, not the developer's real one.
    os.environ["REDIS_URL"] = get_settings().redis_url.rsplit("/", 1)[0] + "/15"
    get_settings.cache_clear()

    yield test_database_url

    asyncio.run(drop())


@pytest.fixture
async def session(database: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def client(database: str) -> AsyncIterator[AsyncClient]:
    """In-process HTTP client: no uvicorn, no sockets, no flakiness."""
    from app.core.database import dispose_engine
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await dispose_engine()


@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """A client already registered and carrying a bearer token."""
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/auth/register", json={"email": email, "password": "supersecret123"}
    )
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


@pytest.fixture
async def project(auth_client: AsyncClient) -> dict:
    response = await auth_client.post(
        "/api/projects", json={"title": "Test project", "target_duration": 30}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(autouse=True)
def _no_background_thumbnails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generating a script queues a cover; tests must not touch the real queue."""

    async def _skip(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.api.routes.generation.enqueue", _skip)


@pytest.fixture(autouse=True)
def _fresh_telemetry_recorder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test gets its own recorder, so events never leak between tests."""
    import app.services.telemetry.recorder as recorder

    monkeypatch.setattr(recorder, "_recorder", recorder.Recorder())


@pytest.fixture(autouse=True)
async def _fresh_database_engine(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """pytest runs each test in its own event loop, and an engine's connections
    belong to the loop that opened them. Start every test with no cached engine and
    close whatever it opened, so code that uses the global engine (the telemetry
    recorder, background tasks) never touches a connection from an earlier loop."""
    import app.core.database as db

    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_session_factory", None)
    yield
    await db.dispose_engine()
