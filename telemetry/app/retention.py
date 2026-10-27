"""Deleting old events, once a day."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.config import get_settings
from app.database import SessionLocal
from app.models.event import Event

log = logging.getLogger("telemetry.retention")
settings = get_settings()


async def purge(now: datetime | None = None) -> int:
    """Deletes events older than RETENTION_DAYS. Returns how many."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=settings.retention_days)
    async with SessionLocal() as db:
        result = await db.execute(delete(Event).where(Event.created_at < cutoff))
        await db.commit()
    removed = result.rowcount or 0
    if removed:
        log.info(
            "retention: deleted %d events older than %d days", removed, settings.retention_days
        )
    return removed


async def purge_forever() -> None:
    while True:
        try:
            if settings.retention_enabled:
                await purge()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - housekeeping must never take the service down
            log.exception("retention purge failed")
        await asyncio.sleep(24 * 3600)
