"""Shared schema building blocks."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for response models read directly from SQLAlchemy objects.

    `from_attributes=True` lets Pydantic read ORM attributes instead of dict keys,
    so a route can `return project` and FastAPI serialises it through this schema.
    """

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Documents the single error envelope in the OpenAPI schema."""

    error: ErrorDetail
