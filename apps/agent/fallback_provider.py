import logging

from apps.agent.base import LLMProvider

logger = logging.getLogger(__name__)


class FallbackLLMProvider(LLMProvider):
    """Wraps a primary provider with a secondary one to retry on — for
    transient failures on the primary vendor's side (rate limits, momentary
    outages) rather than a real code bug. Confirmed real: three consecutive
    days of Gemini digest-build calls failed in production, then succeeded
    when the exact same call was replayed later with identical input."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self._primary = primary
        self._fallback = fallback

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        try:
            return self._primary.summarize(system_prompt, content, max_tokens=max_tokens)
        except Exception:
            logger.warning("Primary LLM provider failed on summarize() — retrying with fallback", exc_info=True)
            return self._fallback.summarize(system_prompt, content, max_tokens=max_tokens)

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        try:
            return self._primary.generate(system_prompt, user_prompt, max_tokens=max_tokens)
        except Exception:
            logger.warning("Primary LLM provider failed on generate() — retrying with fallback", exc_info=True)
            return self._fallback.generate(system_prompt, user_prompt, max_tokens=max_tokens)
