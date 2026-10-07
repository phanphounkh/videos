"""Asset schemas."""

import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class AssetResponse(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    scene_id: uuid.UUID | None
    type: str
    source: str
    storage_key: str
    mime_type: str
    size_bytes: int
    duration: float | None
    width: int | None
    height: int | None
    original_filename: str | None
    provider: str | None
    url: str | None
    created_at: datetime
