import logging
import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()
log = logging.getLogger("telemetry.db")

engine = create_async_engine(
    settings.database_url, echo=False, pool_size=10, max_overflow=10, pool_pre_ping=True
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start", []).append(time.monotonic())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after(conn, cursor, statement, parameters, context, executemany):
    started = conn.info.get("query_start")
    if not started:
        return
    elapsed_ms = (time.monotonic() - started.pop()) * 1000
    if elapsed_ms >= settings.slow_query_threshold_ms:
        log.warning("slow query (%.0f ms): %s", elapsed_ms, statement[:300].replace("\n", " "))


async def get_db():
    async with SessionLocal() as session:
        yield session
