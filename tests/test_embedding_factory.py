import pytest

from apps.agent.embedding_factory import get_embedding_provider
from apps.agent.embedding_gemini import GeminiEmbeddingProvider
from apps.agent.embedding_openai import OpenAIEmbeddingProvider
from apps.core.config import Settings


def test_returns_openai_embedding_provider_when_configured():
    settings = Settings(embedding_provider="openai", openai_api_key="test-key")
    provider = get_embedding_provider(settings)
    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.dimension == settings.embedding_dim


def test_returns_gemini_embedding_provider_when_configured():
    settings = Settings(embedding_provider="gemini", gemini_api_key="test-key", embedding_dim=768)
    provider = get_embedding_provider(settings)
    assert isinstance(provider, GeminiEmbeddingProvider)
    assert provider.dimension == 768


def test_unknown_embedding_provider_raises():
    settings = Settings(embedding_provider="not-a-real-provider")
    with pytest.raises(ValueError):
        get_embedding_provider(settings)


def test_missing_api_key_raises():
    settings = Settings(embedding_provider="openai", openai_api_key=None)
    with pytest.raises(ValueError):
        get_embedding_provider(settings)


def test_missing_gemini_api_key_raises():
    settings = Settings(embedding_provider="gemini", gemini_api_key=None)
    with pytest.raises(ValueError):
        get_embedding_provider(settings)
