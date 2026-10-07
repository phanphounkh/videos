"""LLM providers and the factory that picks one from configuration."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.ai.base import LLMProvider
from app.services.ai.llm.mock import MockLLMProvider
from app.services.ai.llm.openrouter import OpenRouterLLMProvider

__all__ = ["LLMProvider", "MockLLMProvider", "OpenRouterLLMProvider", "get_llm_provider"]


@lru_cache
def get_llm_provider() -> LLMProvider:
    """LLM_PROVIDER=mock|openrouter. Mock needs no key and costs nothing."""
    if get_settings().llm_provider == "openrouter":
        return OpenRouterLLMProvider()
    return MockLLMProvider()
