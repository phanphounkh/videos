"""Render job schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RenderStatus
from app.schemas.common import ORMModel


class RenderJobResponse(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: RenderStatus
    progress: int
    error_message: str | None
    output_url: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class RenderJobCreatedResponse(BaseModel):
    job_id: uuid.UUID
    status: RenderStatus
