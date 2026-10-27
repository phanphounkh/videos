"""Video purposes: catalogue, project defaults, prompts and the offline writer."""

import json

import pytest
from httpx import AsyncClient

from app.models.enums import VideoPurpose
from app.services.ai import ScriptRequest
from app.services.ai.llm.mock import MockLLMProvider
from app.services.ai.llm.prompts import build_user_prompt, system_prompt
from app.services.purposes import PURPOSES, get_purpose


def test_every_purpose_has_a_template() -> None:
    assert set(PURPOSES) == set(VideoPurpose)


def test_unknown_purpose_falls_back_to_story() -> None:
    assert get_purpose("nonsense").key == VideoPurpose.STORY
    assert get_purpose(None).key == VideoPurpose.STORY


def test_system_prompt_carries_the_purpose_guide() -> None:
    demo = system_prompt("product_demo", False, "en")
    assert "product demo" in demo.lower()
    assert "Never invent features" in demo
    assert "no on-screen host" in demo.lower()
    story = system_prompt("story", True, "km")
    assert "one animated host" in story.lower()
    assert "Khmer requirements" in story
    assert "Khmer requirements" not in demo


def test_user_prompt_reports_purpose_host_and_scene_count() -> None:
    spec = json.loads(
        build_user_prompt(
            prompt="x", duration=60, language="en", style="technology", tone=None,
            audience=None, purpose="social_post", presenter=False,
        ).split("\n\n", 1)[1].rsplit("\n\n", 1)[0]
    )
    assert spec["video_purpose"] == "Social media post"
    assert spec["has_on_screen_host"] is False
    assert spec["target_scene_count"] == 12  # 60s at 5s per scene
    assert spec["tone"] == PURPOSES[VideoPurpose.SOCIAL_POST].tone


@pytest.mark.parametrize("language", ["en", "km"])
@pytest.mark.parametrize("purpose", [p.value for p in VideoPurpose])
async def test_mock_writer_handles_every_purpose(purpose: str, language: str) -> None:
    script = await MockLLMProvider().generate_script(
        ScriptRequest(
            prompt="Sorya video maker", duration=60, language=language,
            style="technology", purpose=purpose, presenter=False,
        )
    )
    assert len(script.scenes) >= 3
    assert abs(script.total_duration - 60) < 2
    assert all(scene.visual_prompt.isascii() for scene in script.scenes)


async def test_purposes_endpoint_lists_templates(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/purposes")
    assert response.status_code == 200
    by_key = {item["key"]: item for item in response.json()}
    assert set(by_key) == {p.value for p in VideoPurpose}
    # A host is on by default for every kind of video now: realistic for demos, cartoon for social.
    assert by_key["product_demo"]["presenter"] is True
    assert by_key["social_post"]["presenter"] is True
    assert by_key["product_demo"]["aspect_ratio"] == "16:9"
    assert by_key["social_post"]["aspect_ratio"] == "9:16"


async def test_project_takes_purpose_defaults(auth_client: AsyncClient) -> None:
    created = await auth_client.post(
        "/api/projects", json={"title": "Launch", "purpose": "product_demo"}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["purpose"] == "product_demo"
    assert body["presenter"] is True
    assert body["cta_text"] == "Try it today"


async def test_project_explicit_presenter_and_cta_win(auth_client: AsyncClient) -> None:
    created = await auth_client.post(
        "/api/projects",
        json={"title": "Launch", "purpose": "product_demo", "presenter": False,
              "cta_text": "Shop now"},
    )
    body = created.json()
    assert body["presenter"] is False
    assert body["cta_text"] == "Shop now"


async def test_existing_style_projects_default_to_story(auth_client: AsyncClient) -> None:
    body = (await auth_client.post("/api/projects", json={"title": "Old"})).json()
    assert (body["purpose"], body["presenter"], body["cta_text"]) == ("story", True, None)


async def test_patch_null_presenter_is_ignored(auth_client: AsyncClient, project: dict) -> None:
    response = await auth_client.patch(
        f"/api/projects/{project['id']}", json={"presenter": None, "purpose": None}
    )
    assert response.status_code == 200
    assert response.json()["presenter"] is True
    assert response.json()["purpose"] == "story"


async def test_unknown_purpose_is_rejected(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/api/projects", json={"title": "x", "purpose": "meme"})
    assert response.status_code == 422
