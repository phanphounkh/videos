"""Every HTTP request becomes an `api_request` event, and gets an id the browser can see.

Pure ASGI (not BaseHTTPMiddleware) so it adds no task or buffering to the request,
and streams (uploads, downloads) are untouched.

For each request this:
  - takes the browser's `X-Request-ID` (or makes one) and returns it as a response
    header, so a failing call seen in the browser can be matched to the server's
    events for it;
  - takes the browser's `X-Telemetry-Session`, so server events carry the same session
    as the click that caused them;
  - binds both (and the user agent) to the ambient context, so every log line and
    event produced while serving the request is stamped with them;
  - after the response, emits one `api_request` event, for ALL requests: unauthenticated
    ones and failures included, since those are exactly what an admin looks for.
"""

import re
import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from app.services.telemetry import context, events
from app.services.telemetry.recorder import record

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

# Not measured: the health probe is noise.
SKIPPED_PREFIXES = ("/api/health",)

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


def _template(scope: Scope, path: str) -> str:
    """The path with every path parameter replaced by its name, or "unmatched".

    Built from the real path rather than `route.path`, because the latter omits the
    router's prefix. Segments are compared whole, so a parameter value that appears
    inside another segment is never touched.
    """
    if scope.get("route") is None:
        return "unmatched"
    params = {str(value): key for key, value in (scope.get("path_params") or {}).items()}
    return "/".join(
        f"{{{params[segment]}}}" if segment in params else segment for segment in path.split("/")
    )


class TelemetryMiddleware:
    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        supplied = _header(scope, b"x-request-id")
        request_id = supplied if supplied and _SAFE_ID.match(supplied) else uuid.uuid4().hex
        session = _header(scope, b"x-telemetry-session")
        session_id = session if session and _SAFE_ID.match(session) else None

        token = context.bind(
            request_id=request_id,
            session_id=session_id,
            user_agent=_header(scope, b"user-agent"),
        )
        started = time.perf_counter()
        status_code = 500
        # The scope is shared with the route, so a dependency can leave the user
        # id in scope["state"] (see get_current_user) for us to read afterwards.
        scope.setdefault("state", {})

        async def capture(message: MutableMapping[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            try:
                self._record(scope, status_code, (time.perf_counter() - started) * 1000)
            except Exception:  # noqa: BLE001 - never break a response over a metric
                pass
            context.reset(token)

    @staticmethod
    def _record(scope: Scope, status_code: int, duration_ms: float) -> None:
        path = scope.get("path", "")
        if path.startswith(SKIPPED_PREFIXES):
            return
        failed = status_code >= 400
        record(
            events.Event(
                name="api_request",
                event_type="product",
                level="error" if status_code >= 500 else "warning" if failed else "info",
                outcome="error" if failed else "ok",
                path=path,
                duration_ms=round(duration_ms),
                user_id=scope.get("state", {}).get("user_id"),
                properties={
                    "method": scope["method"],
                    "route": _template(scope, path),
                    "status_code": status_code,
                },
            )
        )
