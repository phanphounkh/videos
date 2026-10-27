"""What the backend tells the telemetry service, and how it is cleaned first.

An `Event` is exactly the wire shape of telemetry/app/schemas/event.py (`EventIn`):
`wire()` turns it into the JSON that is XADDed onto the Redis stream. Keep the two in
step by hand. The service validates strictly (`extra="forbid"`), so a field added on
only one side is caught loudly instead of silently dropped.
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import PurePath
from typing import Any

EVENT_TYPES = ("llm_usage", "product", "log")
LEVELS = ("debug", "info", "warning", "error")
OUTCOMES = ("ok", "error")

MAX_PROPS = 40
MAX_STRING = 1000
MAX_DEPTH = 3
MAX_ITEMS = 20

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_SECRET = re.compile(
    r"(?:eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*|Bearer\s+[A-Za-z0-9._~+/=-]{8,})"
)
# Keys whose values are never sent, whatever they hold.
_SECRET_KEYS = re.compile(r"(password|passwd|secret|token|api_?key|authorization|cookie)", re.I)


def scrub(text: str) -> str:
    """Emails become [email]; JWTs and `Bearer ...` credentials become [token].

    The telemetry service scrubs again on arrival (it does not trust its senders), but
    the best place to stop a secret is before it leaves the process."""
    return _SECRET.sub("[token]", _EMAIL.sub("[email]", text))


def jsonable(value: Any, depth: int = 0) -> Any:
    """`value` as JSON-safe data: ids and times as text, containers bounded, strings
    scrubbed and cut. Never raises."""
    try:
        if value is None or isinstance(value, bool | int):
            return value
        if isinstance(value, float):
            return value if value == value and abs(value) != float("inf") else None
        if isinstance(value, str):
            return scrub(value)[:MAX_STRING]
        if isinstance(value, uuid.UUID | PurePath):
            return str(value)
        if isinstance(value, datetime | date):
            return value.isoformat()
        if isinstance(value, BaseException):
            return scrub(f"{type(value).__name__}: {value}")[:MAX_STRING]
        if depth >= MAX_DEPTH:
            return scrub(str(value))[:200]
        if isinstance(value, dict):
            return {
                scrub(str(k))[:80]: (
                    "[redacted]" if _SECRET_KEYS.search(str(k)) else jsonable(v, depth + 1)
                )
                for k, v in list(value.items())[:MAX_ITEMS]
            }
        if isinstance(value, list | tuple | set | frozenset):
            return [jsonable(v, depth + 1) for v in list(value)[:MAX_ITEMS]]
        return scrub(repr(value))[:200]
    except Exception:  # noqa: BLE001 - describing a value must never break the caller
        return "[unserialisable]"


def clean_props(props: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (props or {}).items():
        if len(out) >= MAX_PROPS:
            break
        name = scrub(str(key))[:80]
        out[name] = "[redacted]" if _SECRET_KEYS.search(name) else jsonable(value)
    return out


@dataclass(slots=True)
class Event:
    name: str
    event_type: str = "product"
    level: str = "info"
    outcome: str | None = None

    user_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None

    path: str | None = None
    duration_ms: int | None = None

    model: str | None = None
    provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    cost_usd: float | None = None

    properties: dict[str, Any] = field(default_factory=dict)
    user_agent: str | None = None
    # backend or worker; filled in from the process when left empty.
    source: str | None = None
    ts: float = field(default_factory=time.time)

    def wire(self) -> dict[str, Any]:
        """The JSON object XADDed to the stream. Empty fields are left out."""
        data: dict[str, Any] = {
            "event_type": self.event_type if self.event_type in EVENT_TYPES else "product",
            "name": scrub(self.name)[:100] or "unnamed",
            "level": self.level if self.level in LEVELS else "info",
            "ts": self.ts,
            "properties": clean_props(self.properties),
        }
        if self.outcome in OUTCOMES:
            data["outcome"] = self.outcome
        optional = {
            "source": self.source,
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "path": scrub(self.path)[:300] if self.path else None,
            "duration_ms": max(0, int(self.duration_ms)) if self.duration_ms is not None else None,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "finish_reason": self.finish_reason,
            "cost_usd": self.cost_usd,
            "user_agent": self.user_agent[:512] if self.user_agent else None,
        }
        data.update({k: v for k, v in optional.items() if v is not None})
        return data
