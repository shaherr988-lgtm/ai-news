from apps.agent.base import LLMProvider
from apps.core.config import Settings, get_settings


def _build_provider(name: str, settings: Settings) -> LLMProvider:
    name = name.lower().strip()

    if name == "openai":
        from apps.agent.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key or "", model=settings.openai_model)

    if name == "anthropic":
        from apps.agent.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.anthropic_api_key or "", model=settings.anthropic_model
        )

    if name == "gemini":
        from apps.agent.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=settings.gemini_api_key or "", model=settings.gemini_model)

    if name == "deepseek":
        from apps.agent.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider(api_key=settings.deepseek_api_key or "", model=settings.deepseek_model)

    raise ValueError(f"Unknown provider: {name!r} (expected 'openai', 'anthropic', 'gemini', or 'deepseek')")


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return the configured LLMProvider instance, chosen by settings.llm_provider.

    This is the ONE place that decides the provider — switching is a one-line
    .env change (LLM_PROVIDER=openai|anthropic|gemini|deepseek), no code edits.

    If settings.llm_fallback_provider is also set, the returned provider
    retries on that second provider whenever the primary's call raises —
    covering a transient failure (rate limit, momentary outage) on the
    primary vendor's side without needing a second manual run.
    """
    settings = settings or get_settings()
    primary = _build_provider(settings.llm_provider, settings)

    if not settings.llm_fallback_provider:
        return primary

    from apps.agent.fallback_provider import FallbackLLMProvider

    fallback = _build_provider(settings.llm_fallback_provider, settings)
    return FallbackLLMProvider(primary, fallback)
