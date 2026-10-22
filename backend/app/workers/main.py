"""ARQ worker entrypoint.

Run it with:

    uv run arq app.workers.main.WorkerSettings

The worker is a separate PROCESS from the API. It shares the same code (models,
services, providers) but has no HTTP server, so a 20-minute render cannot block
a single API request.
"""

from typing import Any

from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.logging import configure_logging, get_logger
from app.services.queue import redis_settings
from app.services.storage import get_storage
from app.workers.tasks import (
    generate_project_media,
    generate_scene_media,
    generate_thumbnail,
    render_project,
)

log = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    settings = get_settings()
    # Make sure the bucket exists before any job tries to upload into it.
    await get_storage().ensure_ready()
    log.info("worker_startup", environment=settings.environment)


async def shutdown(ctx: dict[str, Any]) -> None:
    await dispose_engine()
    log.info("worker_shutdown")


class WorkerSettings:
    functions = [render_project, generate_scene_media, generate_project_media, generate_thumbnail]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()

    # Rendering is CPU and memory heavy: one job at a time per worker. Scale by
    # running more worker containers, not by raising this number.
    max_jobs = 1
    job_timeout = 3600
    keep_result = 3600
    # A render that dies is not silently retried twice - the user retries.
    max_tries = 1
