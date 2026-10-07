"""Redis job queue (ARQ).

Redis in one sentence: an in-memory key/value store; here it is the mailbox the
API drops jobs into and the worker reads from.

ARQ in one sentence: an asyncio-native task queue - a task is just an `async def`
that ARQ serialises onto Redis and a worker process executes later.

WHY a queue at all: image generation, TTS and rendering take seconds to minutes.
An HTTP request must never wait for them (requirement #33), so the API enqueues
and returns a job id immediately.
"""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_pool: ArqRedis | None = None


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def get_queue() -> ArqRedis:
    """One shared connection pool per process."""
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def close_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def enqueue(task_name: str, *args: object, **kwargs: object) -> str | None:
    """Enqueue a job and return its ARQ id (None if ARQ de-duplicated it)."""
    queue = await get_queue()
    job = await queue.enqueue_job(task_name, *args, **kwargs)
    job_id = job.job_id if job else None
    log.info("job_enqueued", task=task_name, job_id=job_id)
    return job_id
