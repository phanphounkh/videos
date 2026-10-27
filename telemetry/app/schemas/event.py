"""The wire shape of an event on the Redis stream.

The backend and the worker build exactly this (backend/app/services/telemetry/events.py)
and XADD it as the `payload` field of a stream entry. Keep the two in step by hand:
`extra="forbid"` means a field one side forgot is caught at ingest, loudly, instead of
silently dropped.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EventType = Literal["llm_usage", "product", "log"]
Source = Literal["backend", "worker", "frontend"]
Level = Literal["debug", "info", "warning", "error"]
Outcome = Literal["ok", "error"]

LEVELS: tuple[str, ...] = ("debug", "info", "warning", "error")


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    name: str = Field(min_length=1, max_length=100)
    source: Source = "backend"
    level: Level = "info"
    outcome: Outcome | None = None

    user_id: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)
    request_id: str | None = Field(default=None, max_length=64)

    path: str | None = Field(default=None, max_length=300)
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)

    model: str | None = None
    provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    cost_usd: float | None = None

    properties: dict[str, Any] | None = None

    # Raw User-Agent; classified into platform / os / browser here (never stored raw).
    user_agent: str | None = Field(default=None, max_length=512)
    # When it happened, seconds since the epoch. Clamped on ingest: a wrong clock must
    # not put an event in the future or years in the past.
    ts: float | None = None
