"""Health and readiness endpoints.

WHAT: `/api/health` (liveness) and `/api/health/ready` (readiness).
WHY:  Docker Compose, and later any orchestrator, needs a cheap endpoint to know
      the process is up; readiness will additionally check Postgres/Redis once
      those are wired in (Phase 2/4).
"""

from fastapi import APIRouter

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    settings: Settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
        version="0.1.0",
    )


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def ready() -> ReadyResponse:
    # Phase 1 has no dependencies to check yet. Phase 2/4 add database and redis
    # checks here; the response shape is already designed for that.
    return ReadyResponse(status="ok", checks={"api": "ok"})
