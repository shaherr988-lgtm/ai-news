from google import genai
from google.genai import types

from apps.agent.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Free-tier-friendly alternative to OpenAI/Anthropic for summarization —
    an aistudio.google.com API key works without adding billing."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required to use the Gemini provider")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    # gemini-3.6-flash always spends part of the token budget on internal
    # "thinking" before the visible answer, and that spend counts against
    # max_output_tokens (it isn't a separate budget, and this model rejects
    # thinking_budget=0) — a request with only e.g. 300 tokens can burn ~285
    # of them on thinking and get cut off mid-sentence with zero visible
    # output. Pad generously so `max_tokens` still means "visible output
    # budget" the way callers expect, matching OpenAI/Anthropic's providers.
    _THINKING_TOKEN_BUFFER = 2048

    def _generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens + self._THINKING_TOKEN_BUFFER,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            # A larger prompt (e.g. a 30-article digest) can push "thinking"
            # past even a generous buffer, hitting MAX_TOKENS before any
            # visible text is written — response.text is then None/"" with
            # no exception raised. Silently accepting that as "the summary"
            # is how a digest with a real article_count ended up saved with
            # an empty summary_text. Raise instead so callers' fallback logic
            # (agent/prompts + digest_builder's plain-digest path) kicks in.
            finish_reason = getattr(response.candidates[0], "finish_reason", None) if response.candidates else None
            raise RuntimeError(f"Gemini returned no visible text (finish_reason={finish_reason})")
        return text

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        return self._generate(system_prompt, content, max_tokens)

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        return self._generate(system_prompt, user_prompt, max_tokens)
