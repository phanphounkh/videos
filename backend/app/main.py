"""FastAPI application factory.

WHAT: builds the ASGI app: logging, CORS, error handlers, routers, lifespan.
WHY:  a factory function (instead of module-level setup) lets tests build an
      isolated app instance, and keeps `main.py` free of business logic.
HOW:  run it with
          uv run uvicorn app.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook.

    Later phases open the database engine, the Redis pool and the S3 client here
    so they are created once per process and closed cleanly on shutdown.
    """
    settings = get_settings()
    log.info("app_startup", environment=settings.environment, app=settings.app_name)
    yield
    # Close the database connection pool so the process can exit cleanly.
    await dispose_engine()
    log.info("app_shutdown")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI Video Studio API - prompt to rendered MP4.",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    return app


app = create_app()
