"""FastAPI dependencies: the request-scoped objects routes ask for.

Dependency injection in one sentence: a route declares what it needs
(`current_user: CurrentUser`) and FastAPI builds it, so the route never reaches
for globals and tests can override any piece.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.telemetry import context as telemetry_context

# auto_error=False: we raise our own AuthenticationError so the body uses the
# project-wide error envelope instead of FastAPI's {"detail": ...}.
bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token.")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise AuthenticationError("Malformed token subject.", code="INVALID_TOKEN") from exc

    user = await UserRepository(session).get(user_id)
    if user is None:
        raise AuthenticationError("User no longer exists.", code="INVALID_TOKEN")
    if not user.is_active:
        raise PermissionDeniedError("This account is disabled.", code="ACCOUNT_DISABLED")
    # Left in the shared ASGI scope for the telemetry middleware, which measures the
    # request after it finishes and has no other way to know who made it.
    request.scope.setdefault("state", {})["user_id"] = user.id
    # ...and in the ambient context, so every event from here on carries the user.
    telemetry_context.bind(user_id=str(user.id))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    """Telemetry is operational data about every user: admins only."""
    if not user.is_admin:
        raise PermissionDeniedError("This area is for administrators.", code="ADMIN_ONLY")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
