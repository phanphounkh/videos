import json
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import text


async def seed(*items: dict) -> None:
    """Insert events with exact timestamps, bypassing ingest."""
    from app.database import SessionLocal

    async with SessionLocal() as db:
        for item in items:
            values = {
                "id": uuid.uuid4(),
                "event_type": "product",
                "name": "evt",
                "source": "backend",
                "level": "info",
                "outcome": None,
                "user_id": None,
                "session_id": None,
                "request_id": None,
                "path": None,
                "duration_ms": None,
                "model": None,
                "provider": None,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "cost_usd": None,
                "platform": None,
                "browser": None,
                "created_at": datetime.now(UTC) - timedelta(minutes=5),
                **item,
            }
            values["properties"] = json.dumps(
                values.pop("props", None) or item.get("properties") or {}
            )
            await db.execute(
                text(
                    "INSERT INTO events (id, event_type, name, source, level, outcome, user_id,"
                    " session_id, request_id, path, duration_ms, model, provider, prompt_tokens,"
                    " completion_tokens, total_tokens, cost_usd, platform, browser, properties,"
                    " created_at) VALUES (:id, :event_type, :name, :source, :level, :outcome,"
                    " :user_id, :session_id, :request_id, :path, :duration_ms, :model, :provider,"
                    " :prompt_tokens, :completion_tokens, :total_tokens, :cost_usd, :platform,"
                    " :browser, CAST(:properties AS jsonb), :created_at)"
                ),
                values,
            )
        await db.commit()


async def all_events() -> list[dict]:
    from app.database import SessionLocal

    async with SessionLocal() as db:
        result = await db.execute(text("SELECT * FROM events ORDER BY seq"))
        return [dict(r) for r in result.mappings().all()]


SECRET = "test-secret-" + "x" * 24  # HS256 wants a key of 32+ bytes


def token_for(user_id: str, *, minutes: int = 60, secret: str = SECRET) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": user_id, "type": "access", "iat": now, "exp": now + minutes * 60},
        secret,
        algorithm="HS256",
    )
