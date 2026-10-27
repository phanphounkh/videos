import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 - registers the models
from app.background import spawn
from app.config import get_settings
from app.ingest.consumer import consume_forever
from app.retention import purge_forever
from app.routes.events import router as events_router
from app.routes.health import router as health_router
from app.routes.ingest import router as ingest_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    spawn(consume_forever())
    spawn(purge_forever())
    yield


app = FastAPI(
    title=settings.app_name,
    description="Ingests every backend, worker and browser event; serves them to the admin panel.",
    docs_url=f"{settings.api_prefix}/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json" if settings.enable_docs else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ingest_router, prefix=settings.api_prefix)
app.include_router(events_router, prefix=settings.api_prefix)
app.include_router(health_router, prefix=settings.api_prefix)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=settings.env == "dev")  # noqa: S104
