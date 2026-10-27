import asyncio

import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.config import get_settings
from app.database import SessionLocal
from app.ingest.consumer import STATUS
from app.models.event import Event
from auth.deps import AdminToken

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


async def _check_db() -> dict:
    try:
        async with SessionLocal() as db:
            await asyncio.wait_for(db.execute(text("SELECT 1")), 3)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]}


async def _check_redis() -> dict:
    r = redis.Redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
    )
    try:
        await r.ping()
        key = settings.telemetry_stream_key
        length = await r.xlen(key) if await r.exists(key) else 0
        pending = 0
        try:
            info = await r.xpending(key, settings.telemetry_consumer_group)
            pending = int(info["pending"]) if info else 0
        except redis.ResponseError:
            pass  # the group does not exist until the consumer first connects
        return {"ok": True, "stream_length": length, "pending": pending}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]}
    finally:
        await r.aclose()


@router.get("")
async def health():
    """Liveness for the container healthcheck: no auth, no detail."""
    db = await _check_db()
    return {"status": "ok" if db["ok"] else "degraded", "database": db["ok"]}


@router.get("/checks")
async def checks(_: AdminToken):
    """The way to tell "no events" from "the consumer is dead": the database, Redis, the
    stream's backlog and what the consumer has done since it started."""
    db, cache = await asyncio.gather(_check_db(), _check_redis())
    stored: dict = {}
    if db["ok"]:
        async with SessionLocal() as session:
            row = (await session.execute(select(func.count(), func.max(Event.created_at)))).one()
        stored = {"events": int(row[0]), "last_event_at": row[1]}
    healthy = db["ok"] and cache["ok"] and STATUS["state"] == "live"
    return {
        "status": "ok" if healthy else "degraded",
        "database": db,
        "redis": cache,
        "consumer": dict(STATUS),
        "stored": stored,
    }
