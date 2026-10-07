"""Password hashing and JWT access tokens.

WHAT: `hash_password` / `verify_password` (bcrypt) and `create_access_token` /
      `decode_access_token` (JWT, HS256).
WHY bcrypt: it is deliberately slow and salted per password, so a stolen database
      cannot be reversed with a rainbow table. We store ONLY the hash.
WHY JWT: the token carries the user id signed with our secret, so the API can
      authenticate a request without a database lookup for the session itself.
      It is a bearer token - treat it like a password: HTTPS only, short-lived.

We use the `bcrypt` package directly rather than passlib, which is unmaintained
and crashes against bcrypt>=4.1 (it reads the removed `bcrypt.__about__`).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

# bcrypt hashes at most 72 bytes of input and silently ignores the rest, so we
# reject longer passwords explicitly instead of pretending to use them.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash in the database - treat as a failed login, never a 500.
        return False


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,                                  # the user id
        "iat": int(now.timestamp()),                     # issued at
        "exp": int(
            (now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()
        ),
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token.", code="INVALID_TOKEN") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Wrong token type.", code="INVALID_TOKEN")
    if not payload.get("sub"):
        raise AuthenticationError("Token is missing a subject.", code="INVALID_TOKEN")
    return payload
