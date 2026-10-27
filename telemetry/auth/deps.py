"""FastAPI dependencies for who is calling."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from auth import backend
from auth.tokens import Principal, bearer, decode


async def optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal | None:
    """The signed-in user, or None. A missing or expired token is not an error here:
    browser telemetry is fire-and-forget and is still accepted anonymously."""
    return decode(bearer(authorization))


async def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """The admin's bearer token (needed again to look up emails). 401 without a valid
    token, 403 when the caller is not an admin."""
    token = bearer(authorization)
    if decode(token) is None or token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue")
    try:
        admin = await backend.is_admin(token)
    except backend.BackendUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Could not check admin rights: the API is unreachable",
        ) from None
    if not admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This area is for administrators")
    return token


AdminToken = Annotated[str, Depends(require_admin)]
