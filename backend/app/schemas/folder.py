"""Folder schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FolderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    project_count: int
    # The picture of the folder's most recently edited project, for its card.
    cover_url: str | None = None
    created_at: datetime
