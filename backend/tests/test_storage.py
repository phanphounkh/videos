"""Storage key layout and public URL construction.

These are pure functions: no network needed, and they guard the one thing that
silently breaks media in production - using the internal endpoint in a URL the
browser has to fetch.
"""

from app.core.config import get_settings
from app.services.storage.base import (
    project_upload_key,
    render_key,
    scene_image_key,
    scene_upload_key,
    scene_voice_key,
    thumbnail_key,
)
from app.services.storage.urls import public_url, renderer_url


def test_key_layout_is_stable() -> None:
    assert scene_image_key("p1", "s1") == "projects/p1/scenes/s1/image.png"
    assert scene_image_key("p1", "s1", "jpg") == "projects/p1/scenes/s1/image.jpg"
    assert scene_voice_key("p1", "s1") == "projects/p1/scenes/s1/voice.mp3"
    assert scene_upload_key("p1", "s1", "a.png") == "projects/p1/scenes/s1/uploads/a.png"
    assert project_upload_key("p1", "a.png") == "projects/p1/uploads/a.png"
    assert render_key("p1", "j1") == "projects/p1/renders/j1.mp4"
    assert thumbnail_key("p1", "j1") == "projects/p1/renders/j1-thumb.jpg"


def test_public_url_uses_the_browser_reachable_base() -> None:
    settings = get_settings()
    url = public_url("projects/p1/scenes/s1/image.png")
    assert url is not None
    assert url.startswith(settings.s3_public_base_url.rstrip("/"))
    assert settings.s3_bucket in url
    # The in-cluster hostname must never leak into a URL the browser loads.
    assert "s3:8333" not in url


def test_public_url_of_nothing_is_none() -> None:
    assert public_url(None) is None
    assert public_url("") is None


def test_renderer_url_uses_the_in_network_endpoint(monkeypatch) -> None:
    """Regression: headless Chromium runs in the worker container, where
    `localhost:9100` is the worker itself - the render then fails with
    "Error loading image with src: ...". The renderer must get the S3 endpoint.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_renderer_base_url", "http://s3:8333")
    monkeypatch.setattr(settings, "s3_public_base_url", "http://localhost:9100")

    key = "projects/p1/scenes/s1/image.png"
    for_renderer = renderer_url(key)
    for_browser = public_url(key)
    assert for_renderer is not None and for_browser is not None
    assert for_renderer.startswith("http://s3:8333/")
    assert for_browser.startswith("http://localhost:9100/")
    assert "localhost" not in for_renderer


def test_renderer_url_falls_back_to_the_s3_endpoint(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_renderer_base_url", "")
    monkeypatch.setattr(settings, "s3_endpoint_url", "http://s3:8333/")
    assert renderer_url("a/b.png") == "http://s3:8333/ai-video-studio/a/b.png"


def test_renderer_url_of_nothing_is_none() -> None:
    assert renderer_url(None) is None
