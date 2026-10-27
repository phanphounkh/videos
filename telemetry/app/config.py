"""Configuration, from the environment (and a local .env when running on the host)."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "Sorya Studio Telemetry"
    api_prefix: str = "/api/v1"
    enable_docs: bool = False
    env: str = "dev"
    port: int = 8006
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5437/telemetry"
    # Queries at or above this log a warning: the admin aggregates are the ones that
    # slow down as the events table grows.
    slow_query_threshold_ms: int = 500

    redis_url: str = "redis://localhost:6381/0"
    telemetry_stream_key: str = "sorya:telemetry:events"
    telemetry_consumer_group: str = "telemetry-ingest"
    # Stable per container, not per process: a restarted worker resumes (and reclaims)
    # the same consumer's unacknowledged entries instead of abandoning them.
    hostname: str = "telemetry-ingest-1"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    backend_url: str = "http://localhost:8000"

    ingest_rate_limit_window_seconds: int = 60
    ingest_rate_limit_max: int = 600
    ingest_anon_rate_limit_max: int = 120
    ingest_max_body_bytes: int = 1024 * 1024
    ingest_max_events_per_batch: int = 500

    retention_days: int = 90
    retention_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
