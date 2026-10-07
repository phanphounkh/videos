"""User queries."""

from sqlalchemy import func, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        # Emails are matched case-insensitively: Foo@x.com and foo@x.com are the
        # same account, which is what users expect.
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        return await self.get_by_email(email) is not None
