"""Per-caller request budgets over a fixed window, counted in Redis.

They exist to stop a runaway or hostile client, not to shape normal traffic (the
browser batches, so one request carries many events). Fails OPEN when Redis is
unreachable: losing abuse protection for a moment beats dropping every browser event
while Redis blips.
"""

import logging
import time

import redis.asyncio as redis
from fastapi import HTTPException, status
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.config import get_settings

log = logging.getLogger("telemetry.ratelimit")
settings = get_settings()

_PREFIX = "telemetry:ratelimit:"
_TIMEOUT_S = 2
_BACKOFF_S = 30

_redis: redis.Redis | None = None
_down_until = 0.0


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=_TIMEOUT_S,
            socket_timeout=_TIMEOUT_S,
            retry=Retry(NoBackoff(), 0),
        )
    return _redis


async def enforce(bucket: str, caller: str, limit: int) -> None:
    global _down_until
    if time.monotonic() < _down_until:
        return
    key = f"{_PREFIX}{bucket}:{caller}"
    try:
        r = _client()
        count = await r.incr(key)
        if count == 1 or await r.ttl(key) < 0:
            await r.expire(key, settings.ingest_rate_limit_window_seconds)
    except redis.RedisError as exc:
        _down_until = time.monotonic() + _BACKOFF_S
        log.warning(
            "rate-limit check failed (%s): not limiting for %ds", type(exc).__name__, _BACKOFF_S
        )
        return
    if count > limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many telemetry requests")


def reset() -> None:
    global _redis, _down_until
    _redis = None
    _down_until = 0.0
