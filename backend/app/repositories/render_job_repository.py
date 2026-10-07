"""RenderJob queries."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.render_job import RenderJob
from app.repositories.base import BaseRepository


class RenderJobRepository(BaseRepository[RenderJob]):
    model = RenderJob

    async def get_with_project(self, job_id: uuid.UUID) -> RenderJob | None:
        stmt = (
            select(RenderJob)
            .where(RenderJob.id == job_id)
            .options(selectinload(RenderJob.project), selectinload(RenderJob.output_asset))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_for_project(self, project_id: uuid.UUID) -> RenderJob | None:
        stmt = (
            select(RenderJob)
            .where(RenderJob.project_id == project_id)
            .order_by(RenderJob.created_at.desc())
            .limit(1)
            .options(selectinload(RenderJob.output_asset))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
