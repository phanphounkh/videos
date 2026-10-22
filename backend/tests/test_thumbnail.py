"""Thumbnail text selection and payload shape (the pixels are drawn by the renderer)."""

from types import SimpleNamespace

from app.models.enums import AspectRatio
from app.services.thumbnail_service import _shorten, thumbnail_payload


def _project(purpose: str, *, hook: str | None = "Wait, what?", **extra):
    scene = SimpleNamespace(scene_number=1, on_screen_text=hook, image_asset=None)
    values = {
        "title": "Turn Any Prompt Into Video with Sorya",
        "purpose": purpose,
        "presenter": False,
        "cta_text": "Try it today",
        "language": "en",
        "scenes": [scene],
        "dimensions": AspectRatio.LANDSCAPE.dimensions,
    }
    return SimpleNamespace(**{**values, **extra})


def test_story_and_social_lead_with_the_hook() -> None:
    for purpose in ("story", "social_post"):
        assert thumbnail_payload(_project(purpose))["headline"] == "Wait, what?"


def test_other_purposes_lead_with_the_title() -> None:
    for purpose in ("product_demo", "creator", "explainer"):
        payload = thumbnail_payload(_project(purpose))
        assert payload["headline"] == "Turn Any Prompt Into Video with Sorya"


def test_missing_hook_falls_back_to_the_title() -> None:
    payload = thumbnail_payload(_project("story", hook=None))
    assert payload["headline"].startswith("Turn Any Prompt")


def test_kicker_names_the_purpose_and_cta_is_passed_through() -> None:
    payload = thumbnail_payload(_project("product_demo"))
    assert payload["kicker"] == "Product demo"
    assert payload["cta"] == "Try it today"
    assert payload["project"]["presenter"] is False


def test_size_keeps_the_aspect_ratio_at_720_short_side() -> None:
    wide = thumbnail_payload(_project("story"))["project"]
    assert (wide["width"], wide["height"]) == (1280, 720)
    tall = thumbnail_payload(_project("story", dimensions=AspectRatio.PORTRAIT.dimensions))
    assert (tall["project"]["width"], tall["project"]["height"]) == (720, 1280)


def test_long_headlines_are_cut_at_a_word_boundary() -> None:
    cut = _shorten("word " * 30)
    assert len(cut) <= 48
    assert not cut.endswith(" ")


def test_khmer_without_spaces_is_hard_cut() -> None:
    assert len(_shorten("ក" * 100)) == 48
