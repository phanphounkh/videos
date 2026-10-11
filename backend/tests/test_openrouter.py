"""OpenRouter request contract without making paid network calls."""

import pytest

from app.core.config import get_settings
from app.core.exceptions import ProviderError
from app.services.ai.base import ScriptRequest
from app.services.ai.llm.openrouter import OpenRouterLLMProvider


def test_openrouter_requires_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "")
    with pytest.raises(ProviderError) as exc:
        OpenRouterLLMProvider()
    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"


def test_openrouter_uses_strict_story_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "openrouter_api_key", "test-only-key")
    monkeypatch.setattr(settings, "openrouter_model", "openai/gpt-4o-mini")
    provider = OpenRouterLLMProvider()

    body = provider._request_body(
        ScriptRequest(
            prompt="រឿងខ្មោចកំប្លែងនៅភូមិមួយ",
            duration=60,
            language="km",
            style="social_media",
            tone="funny and suspenseful",
            audience="Khmer viewers",
        )
    )

    assert body["model"] == "openai/gpt-4o-mini"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["provider"] == {"require_parameters": True}
    assert "រឿងខ្មោចកំប្លែងនៅភូមិមួយ" in body["messages"][1]["content"]
    assert "one continuous story" in body["messages"][0]["content"].lower()
