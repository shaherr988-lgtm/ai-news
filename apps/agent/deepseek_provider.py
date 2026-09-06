from openai import OpenAI

from apps.agent.base import LLMProvider

# DeepSeek's API is OpenAI-compatible (same request/response shape) — the
# official SDK for it is just the `openai` package pointed at DeepSeek's
# base_url, per DeepSeek's own docs.
_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required to use the DeepSeek provider")
        self._client = OpenAI(api_key=api_key, base_url=_DEEPSEEK_BASE_URL)
        self._model = model

    def _chat(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        return self._chat(system_prompt, content, max_tokens)

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        return self._chat(system_prompt, user_prompt, max_tokens)
