"""Async SQLAlchemy engine, session factory and FastAPI dependency.

WHAT: one async engine per process, a session factory, and `get_session()` which
      FastAPI injects into routes.
WHY:  creating an engine per request would open a new connection pool every time.
      One engine + one session per request is the standard shape: the session is
      a unit of work that is committed or rolled back exactly once.
HOW:  in a route:

          async def handler(session: AsyncSession = Depends(get_session)): ...

`expire_on_attributes=False` (expire_on_commit=False) matters: without it, every
attribute access AFTER commit triggers a fresh lazy SELECT, which inside an async
request raises MissingGreenlet. With it, we can safely serialise the object we
just committed.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            pool_pre_ping=True,  # drop dead connections instead of erroring mid-query
            pool_size=10,
            max_overflow=5,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, always closed."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Close the pool on shutdown so the process can exit cleanly."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
