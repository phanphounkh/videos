"""Project queries.

Every lookup here is scoped by `owner_id`. That is the core authorization rule:
a user can only ever reach their own projects, enforced in the WHERE clause
rather than by an `if` after the fetch (which is easy to forget).
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.scene import Scene
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_for_owner(
        self, project_id: uuid.UUID, owner_id: uuid.UUID, *, include_trashed: bool = False
    ) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.id == project_id, Project.owner_id == owner_id)
            .options(selectinload(Project.scenes).selectinload(Scene.captions))
            # populate_existing: refresh an instance already in the identity map
            # instead of returning its possibly stale loaded collections.
            .execution_options(populate_existing=True)
        )
        if not include_trashed:
            # A trashed project is gone as far as every other endpoint is concerned.
            stmt = stmt.where(Project.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def _filtered(
        self,
        owner_id: uuid.UUID,
        *,
        view: str = "all",
        folder: uuid.UUID | str | None = None,
        q: str | None = None,
    ):
        """The WHERE clauses behind the list: view (all/recent/starred/trash), folder
        (an id, or "none" for projects in no folder) and a title search."""
        where = [Project.owner_id == owner_id]
        if view == "trash":
            where.append(Project.deleted_at.is_not(None))
        else:
            where.append(Project.deleted_at.is_(None))
        if view == "starred":
            where.append(Project.starred.is_(True))
        if view == "recent":
            where.append(Project.updated_at >= datetime.now(UTC) - timedelta(days=30))
        if folder == "none":
            where.append(Project.folder_id.is_(None))
        elif folder:
            where.append(Project.folder_id == folder)
        if q:
            like = "%" + q.strip().replace("%", "").replace("_", "") + "%"
            where.append(Project.title.ilike(like))
        return where

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        view: str = "all",
        folder: uuid.UUID | str | None = None,
        q: str | None = None,
        sort: str = "recent",
    ) -> Sequence[Project]:
        order = {
            "title": Project.title.asc(),
            "created": Project.created_at.desc(),
            "trashed": Project.deleted_at.desc(),
        }.get(sort, Project.updated_at.desc())
        stmt = (
            select(Project)
            .where(*self._filtered(owner_id, view=view, folder=folder, q=q))
            .order_by(order)
            .limit(limit)
            .offset(offset)
            .options(selectinload(Project.scenes))
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def count_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        view: str = "all",
        folder: uuid.UUID | str | None = None,
        q: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Project)
            .where(*self._filtered(owner_id, view=view, folder=folder, q=q))
        )
        return int((await self.session.execute(stmt)).scalar_one())
