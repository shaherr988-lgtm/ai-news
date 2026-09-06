from apps.agent.embedding_base import EmbeddingProvider
from apps.core.config import Settings, get_settings


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Return the configured EmbeddingProvider instance: "openai" or "gemini".

    Adding another provider (e.g. a local sentence-transformers model, or
    Voyage AI) means: writing a new class implementing EmbeddingProvider in
    its own module, then adding one more branch here — same pattern as
    apps/agent/factory.py.
    """
    settings = settings or get_settings()
    provider = settings.embedding_provider.lower().strip()

    if provider == "openai":
        from apps.agent.embedding_openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key or "",
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dim,
        )

    if provider == "gemini":
        from apps.agent.embedding_gemini import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key or "",
            model=settings.gemini_embedding_model,
            dimension=settings.embedding_dim,
        )

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider!r} (expected 'openai' or 'gemini')"
    )
