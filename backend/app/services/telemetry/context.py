"""Who and what the code running RIGHT NOW is working on.

The middleware sets the request id and the browser's session id once per request;
the auth dependency adds the user. From then on every event emitted anywhere below
(a log line deep in a service, an AI call, a render) is stamped with them, with no
parameter threaded through any function. That is what lets an admin follow one click
in the browser through to everything the server did because of it.

ContextVars propagate through asyncio tasks and `asyncio.to_thread`, which are the
boundaries a request crosses.
"""

import contextvars
from typing import Any

_ctx: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "telemetry_ctx", default=None
)

# Which process this is: "backend" (the API) or "worker" (render/generation jobs).
_source = "backend"


def set_source(source: str) -> None:
    global _source
    _source = source


def source() -> str:
    return _source


def current() -> dict[str, Any]:
    return _ctx.get() or {}


def bind(**values: Any) -> contextvars.Token:
    """Adds to the ambient context; returns a token for `reset`."""
    return _ctx.set({**current(), **{k: v for k, v in values.items() if v is not None}})


def reset(token: contextvars.Token) -> None:
    _ctx.reset(token)


class telemetry_context:
    """`with telemetry_context(user_id=..., session_id=...):` for the duration of a block
    (a background job, a script)."""

    def __init__(self, **values: Any) -> None:
        self._values = values
        self._token: contextvars.Token | None = None

    def __enter__(self) -> "telemetry_context":
        self._token = bind(**self._values)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._token is not None:
            reset(self._token)
