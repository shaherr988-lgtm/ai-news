import pytest

from apps.agent.anthropic_provider import AnthropicProvider
from apps.agent.factory import get_llm_provider
from apps.agent.gemini_provider import GeminiProvider
from apps.agent.openai_provider import OpenAIProvider
from apps.core.config import Settings


def test_returns_openai_provider_when_configured():
    settings = Settings(llm_provider="openai", openai_api_key="test-key")
    provider = get_llm_provider(settings)
    assert isinstance(provider, OpenAIProvider)


def test_returns_anthropic_provider_when_configured():
    settings = Settings(llm_provider="anthropic", anthropic_api_key="test-key")
    provider = get_llm_provider(settings)
    assert isinstance(provider, AnthropicProvider)


def test_returns_gemini_provider_when_configured():
    settings = Settings(llm_provider="gemini", gemini_api_key="test-key")
    provider = get_llm_provider(settings)
    assert isinstance(provider, GeminiProvider)


def test_unknown_provider_raises():
    settings = Settings(llm_provider="not-a-real-provider")
    with pytest.raises(ValueError):
        get_llm_provider(settings)


def test_missing_api_key_raises():
    settings = Settings(llm_provider="openai", openai_api_key=None)
    with pytest.raises(ValueError):
        get_llm_provider(settings)


def test_missing_gemini_api_key_raises():
    settings = Settings(llm_provider="gemini", gemini_api_key=None)
    with pytest.raises(ValueError):
        get_llm_provider(settings)
