"""Application errors and their HTTP representation.

WHAT: one exception base class (`AppError`) carrying a stable machine-readable
      `code`, plus the FastAPI handlers that turn any failure into the single
      error envelope the frontend expects:

          {"error": {"code": "PROJECT_NOT_FOUND", "message": "Project was not found."}}

WHY:  the frontend should branch on `code`, never on an English sentence or an
      HTTP status alone. A single envelope also means unexpected crashes cannot
      leak stack traces or SQL to the client.
HOW:  services raise `AppError` subclasses; `register_exception_handlers(app)`
      installs the handlers in `app.main`.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

log = get_logger(__name__)


class AppError(Exception):
    """Base class for every expected, domain-level failure."""

    code: str = "INTERNAL_ERROR"
    message: str = "Something went wrong."
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    message = "Resource was not found."
    status_code = 404


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    message = "The request payload is invalid."
    status_code = 422


class AuthenticationError(AppError):
    code = "NOT_AUTHENTICATED"
    message = "Authentication is required."
    status_code = 401


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    message = "You do not have access to this resource."
    status_code = 403


class ConflictError(AppError):
    code = "CONFLICT"
    message = "The resource is in a conflicting state."
    status_code = 409


class ProviderError(AppError):
    """An external AI / storage / render provider failed."""

    code = "PROVIDER_ERROR"
    message = "An upstream provider failed. Please retry."
    status_code = 502


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_ERROR",
                "The request payload is invalid.",
                {"fields": [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {401: "NOT_AUTHENTICATED", 403: "PERMISSION_DENIED", 404: "NOT_FOUND"}
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                codes.get(exc.status_code, f"HTTP_{exc.status_code}"),
                str(exc.detail),
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the real cause server-side, return nothing sensitive to the client.
        log.exception("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "Something went wrong."),
        )
