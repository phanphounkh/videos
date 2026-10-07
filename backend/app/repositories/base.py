"""Generic repository.

WHAT: thin typed CRUD helpers over one SQLAlchemy model.
WHY:  services should express intent ("get this user's projects"), not assemble
      SELECT statements inline. Keeping queries here means one place to optimise,
      and services stay readable and testable.
      This is intentionally thin - we are not building an ORM on top of the ORM.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


# PEP 695 generics (Python 3.12+): `BaseRepository[User]` is typed end to end.
class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: Any = None,
        **filters: Any,
    ) -> Sequence[ModelT]:
        stmt = select(self.model).filter_by(**filters).limit(limit).offset(offset)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return int((await self.session.execute(stmt)).scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        """Stage an insert. The caller commits - one transaction per request."""
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)

    async def delete_where(self, **filters: Any) -> int:
        result = await self.session.execute(delete(self.model).filter_by(**filters))
        return int(result.rowcount or 0)
