from apps.agent.base import LLMProvider
from apps.core.config import Settings, get_settings


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return the configured LLMProvider instance, chosen by settings.llm_provider.

    This is the ONE place that decides the provider — switching is a one-line
    .env change (LLM_PROVIDER=openai|anthropic|gemini), no code edits.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "openai":
        from apps.agent.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=settings.openai_api_key or "", model=settings.openai_model)

    if provider == "anthropic":
        from apps.agent.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.anthropic_api_key or "", model=settings.anthropic_model
        )

    if provider == "gemini":
        from apps.agent.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=settings.gemini_api_key or "", model=settings.gemini_model)

    if provider == "deepseek":
        from apps.agent.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider(api_key=settings.deepseek_api_key or "", model=settings.deepseek_model)

    raise ValueError(
        f"Unknown LLM_PROVIDER: {settings.llm_provider!r} "
        "(expected 'openai', 'anthropic', 'gemini', or 'deepseek')"
    )
