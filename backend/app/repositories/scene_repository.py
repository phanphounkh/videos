"""Scene queries."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.scene import Scene
from app.repositories.base import BaseRepository


class SceneRepository(BaseRepository[Scene]):
    model = Scene

    async def get_with_project(self, scene_id: uuid.UUID) -> Scene | None:
        """Load the scene together with its project, needed for ownership checks."""
        stmt = (
            select(Scene)
            .where(Scene.id == scene_id)
            .options(selectinload(Scene.project), selectinload(Scene.captions))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_project(self, project_id: uuid.UUID) -> Sequence[Scene]:
        stmt = (
            select(Scene)
            .where(Scene.project_id == project_id)
            .order_by(Scene.scene_number)
            .options(selectinload(Scene.captions))
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def next_scene_number(self, project_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(Scene.scene_number), 0)).where(
            Scene.project_id == project_id
        )
        return int((await self.session.execute(stmt)).scalar_one()) + 1

    async def delete_for_project(self, project_id: uuid.UUID) -> int:
        return await self.delete_where(project_id=project_id)
