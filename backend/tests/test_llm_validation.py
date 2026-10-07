"""LLM output validation - the project's most important safety boundary.

These tests encode the rule "never trust LLM-generated JSON": malformed,
fenced, truncated or structurally wrong output must be rejected or repaired,
never persisted as-is.
"""

import pytest

from app.core.exceptions import ProviderError
from app.schemas.generation import GeneratedScript
from app.services.ai.base import ScriptRequest
from app.services.ai.llm.mock import MockLLMProvider
from app.services.ai.llm.parsing import extract_json_object, parse_script

VALID = """
{
  "title": "Machine Learning Explained",
  "description": "A beginner-friendly introduction.",
  "language": "en",
  "estimated_duration": 14,
  "scenes": [
    {"scene_number": 1, "narration": "ML learns patterns from data.",
     "visual_prompt": "a computer analysing charts", "on_screen_text": "What is ML?",
     "duration": 7, "transition": "fade"},
    {"scene_number": 2, "narration": "It improves with more examples.",
     "visual_prompt": "rising accuracy graph", "on_screen_text": "Learning",
     "duration": 7, "transition": "fade"}
  ]
}
"""


def test_valid_json_parses() -> None:
    script = parse_script(VALID)
    assert isinstance(script, GeneratedScript)
    assert script.title == "Machine Learning Explained"
    assert script.total_duration == 14


def test_markdown_fences_are_stripped() -> None:
    script = parse_script(f"Here is your script:\n```json\n{VALID}\n```\nEnjoy!")
    assert len(script.scenes) == 2


def test_trailing_commas_are_repaired() -> None:
    broken = VALID.replace('"transition": "fade"}\n  ]', '"transition": "fade"},\n  ]')
    assert len(parse_script(broken).scenes) == 2


def test_prose_only_is_rejected() -> None:
    with pytest.raises(ProviderError) as exc:
        parse_script("I'm sorry, I can't help with that.")
    assert exc.value.code == "INVALID_AI_RESPONSE"


def test_truncated_json_is_rejected() -> None:
    with pytest.raises(ProviderError):
        parse_script(VALID[: len(VALID) // 2])


def test_missing_required_field_is_rejected() -> None:
    with pytest.raises(ProviderError) as exc:
        parse_script('{"title": "x", "scenes": [{"scene_number": 1, "duration": 5}]}')
    assert exc.value.code == "INVALID_AI_RESPONSE"


def test_zero_scenes_is_rejected() -> None:
    with pytest.raises(ProviderError):
        parse_script('{"title": "x", "description": "", "scenes": []}')


def test_json_array_is_rejected() -> None:
    with pytest.raises(ProviderError):
        parse_script("[1, 2, 3]")


def test_scene_numbers_are_renumbered_defensively() -> None:
    duplicated = VALID.replace('"scene_number": 2', '"scene_number": 2').replace(
        '"scene_number": 1', '"scene_number": 7'
    )
    script = parse_script(duplicated)
    assert [scene.scene_number for scene in script.scenes] == [1, 2]


def test_unknown_transition_falls_back_to_fade() -> None:
    script = parse_script(VALID.replace('"fade"', '"explode"'))
    assert all(scene.transition == "fade" for scene in script.scenes)


def test_extract_json_object_handles_surrounding_text() -> None:
    assert extract_json_object('blah {"a": 1} trailing')["a"] == 1


async def test_mock_provider_returns_a_valid_script() -> None:
    script = await MockLLMProvider().generate_script(
        ScriptRequest(prompt="Explain neural networks", duration=60, language="en",
                      style="educational")
    )
    assert script.scenes
    assert abs(script.total_duration - 60) < 2
    # visual prompts stay English even for Khmer narration (image models)
    assert all(scene.visual_prompt.isascii() for scene in script.scenes)


async def test_mock_provider_produces_khmer_for_km() -> None:
    script = await MockLLMProvider().generate_script(
        ScriptRequest(prompt="ប្រវត្តិសាស្ត្រអង្គរវត្ត", duration=30, language="km",
                      style="documentary")
    )
    assert any("\u1780" <= ch <= "\u17ff" for ch in script.scenes[0].narration)
    assert script.scenes[0].visual_prompt.isascii()
