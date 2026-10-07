"""Asset queries."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.asset import Asset
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    async def list_for_project(self, project_id: uuid.UUID) -> Sequence[Asset]:
        stmt = (
            select(Asset)
            .where(Asset.project_id == project_id)
            .order_by(Asset.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def get_by_storage_key(self, storage_key: str) -> Asset | None:
        stmt = select(Asset).where(Asset.storage_key == storage_key)
        return (await self.session.execute(stmt)).scalar_one_or_none()
