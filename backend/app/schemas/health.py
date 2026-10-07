"""Pydantic response models for the health endpoints.

WHY keep these in `schemas/` instead of returning plain dicts: the response shape
becomes part of the OpenAPI document, so the SvelteKit client can be typed
against it, and typos are caught by the type checker instead of at runtime.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    version: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]
