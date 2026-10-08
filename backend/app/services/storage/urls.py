"""Public URLs for stored objects.

Kept separate from the S3 client because building a URL needs no network call
and no credentials - presenters use it on every response.

`S3_PUBLIC_BASE_URL` is the address the BROWSER and the renderer can reach
(e.g. http://localhost:9100), which is NOT the in-network endpoint the backend
uses (http://s3:8333). Mixing those two up is the classic "works in the API,
broken in the browser" bug.
"""

from urllib.parse import quote

from app.core.config import get_settings


def public_url(storage_key: str | None) -> str | None:
    """URL for the BROWSER (API responses, thumbnails, download links)."""
    if not storage_key:
        return None
    settings = get_settings()
    base = settings.s3_public_base_url.rstrip("/")
    return f"{base}/{settings.s3_bucket}/{quote(storage_key)}"


def renderer_url(storage_key: str | None) -> str | None:
    """URL for the RENDERER process, which runs in the worker container.

    Headless Chromium fetches these itself, so they must resolve from inside the
    worker - `http://localhost:9100` there means the worker container, and the
    render fails with "Error loading image with src: ...". In development both
    functions return the same host URL; in Docker this one returns
    `http://s3:8333/...`.
    """
    if not storage_key:
        return None
    settings = get_settings()
    return f"{settings.renderer_media_base_url}/{settings.s3_bucket}/{quote(storage_key)}"
