"""LLM providers and the factory that picks one from configuration."""

from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ai.base import LLMProvider
from app.services.ai.gemini import gemini_configured
from app.services.ai.llm.gemini import GeminiLLMProvider
from app.services.ai.llm.mock import MockLLMProvider
from app.services.ai.llm.openrouter import OpenRouterLLMProvider

log = get_logger(__name__)

__all__ = [
    "GeminiLLMProvider",
    "LLMProvider",
    "MockLLMProvider",
    "OpenRouterLLMProvider",
    "get_llm_provider",
]


@lru_cache
def get_llm_provider() -> LLMProvider:
    """LLM_PROVIDER=mock|openrouter|gemini. Mock needs no key and costs nothing.

    gemini falls back to openrouter while GEMINI_API_KEY is empty, so the key
    can be added later without changing anything else.
    """
    configured = get_settings().llm_provider
    if configured == "gemini":
        if gemini_configured():
            return GeminiLLMProvider()
        log.warning("llm_gemini_key_missing", fallback="openrouter")
        configured = "openrouter"
    if configured == "openrouter":
        return OpenRouterLLMProvider()
    return MockLLMProvider()
