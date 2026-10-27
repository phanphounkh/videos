"""Asking the backend about people: is this caller an admin, and what is this id's email.

The admin panel needs readable names, and admin rights can be revoked while a token is
still valid, so both questions go to the backend (cached for a few seconds so a page
that makes many requests is not many round trips).
"""

import hashlib
import time

import httpx

from app.config import get_settings

_ADMIN_TTL_S = 15
_EMAIL_TTL_S = 120

_admin_cache: dict[str, tuple[float, bool]] = {}
_email_cache: dict[str, tuple[float, str | None]] = {}


class BackendUnavailable(Exception):
    """The backend did not answer, so nothing can be said about the caller."""


def _key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=get_settings().backend_url.rstrip("/"), timeout=3.0)


async def is_admin(token: str) -> bool:
    key = _key(token)
    cached = _admin_cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    try:
        async with _client() as http:
            response = await http.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        raise BackendUnavailable(str(exc)) from exc
    admin = response.status_code == 200 and bool(response.json().get("is_admin"))
    if len(_admin_cache) > 500:
        _admin_cache.clear()
    _admin_cache[key] = (time.monotonic() + _ADMIN_TTL_S, admin)
    return admin


async def emails(token: str, user_ids: list[str]) -> dict[str, str | None]:
    """user id -> email, for the ids the backend knows. Unknown or unreachable: None."""
    now = time.monotonic()
    result: dict[str, str | None] = {}
    missing: list[str] = []
    for uid in dict.fromkeys(user_ids):
        cached = _email_cache.get(uid)
        if cached and cached[0] > now:
            result[uid] = cached[1]
        else:
            missing.append(uid)
    if missing:
        try:
            async with _client() as http:
                response = await http.get(
                    "/api/admin/users/lookup",
                    params={"ids": ",".join(missing[:200])},
                    headers={"Authorization": f"Bearer {token}"},
                )
            found = response.json() if response.status_code == 200 else {}
        except (httpx.HTTPError, ValueError):
            found = {}
        if len(_email_cache) > 5000:
            _email_cache.clear()
        for uid in missing:
            email = found.get(uid)
            result[uid] = email
            if found:  # do not cache a failed lookup as "unknown person"
                _email_cache[uid] = (now + _EMAIL_TTL_S, email)
    return result


def reset_caches() -> None:
    _admin_cache.clear()
    _email_cache.clear()
