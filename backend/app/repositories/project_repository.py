"""Project queries.

Every lookup here is scoped by `owner_id`. That is the core authorization rule:
a user can only ever reach their own projects, enforced in the WHERE clause
rather than by an `if` after the fetch (which is easy to forget).
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.scene import Scene
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_for_owner(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.id == project_id, Project.owner_id == owner_id)
            .options(selectinload(Project.scenes).selectinload(Scene.captions))
            # populate_existing: refresh an instance already in the identity map
            # instead of returning its possibly stale loaded collections.
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_owner(
        self, owner_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> Sequence[Project]:
        stmt = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Project.scenes))
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def count_for_owner(self, owner_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
        return int((await self.session.execute(stmt)).scalar_one())
