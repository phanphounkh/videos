"""Checks the bearer tokens the backend issues.

This service shares the backend's signing secret, so it verifies a token's signature
and expiry itself, with no call to the backend. Whether the caller is an ADMIN is not
in the token (a token outlives a revoked admin): that is asked of the backend, see
auth/backend.py.
"""

from dataclasses import dataclass

import jwt

from app.config import get_settings


@dataclass(frozen=True, slots=True)
class Principal:
    id: str


def decode(token: str | None) -> Principal | None:
    """The token's user, or None when it is missing, malformed, expired or forged."""
    if not token:
        return None
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    if payload.get("type") != "access" or not isinstance(subject, str) or not subject:
        return None
    return Principal(id=subject)


def bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None
