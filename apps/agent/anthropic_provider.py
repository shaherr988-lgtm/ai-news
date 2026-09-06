from anthropic import Anthropic

from apps.agent.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required to use the Anthropic provider")
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def _message(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        return self._message(system_prompt, content, max_tokens)

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        return self._message(system_prompt, user_prompt, max_tokens)
