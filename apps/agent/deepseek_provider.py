from apps.agent.openai_provider import OpenAIProvider

# DeepSeek's API is OpenAI-compatible (same request/response shape) — the
# official SDK for it is just the `openai` package pointed at DeepSeek's
# base_url, per DeepSeek's own docs. Subclassing OpenAIProvider and only
# overriding the client construction avoids duplicating _chat/summarize/generate.
_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is required to use the DeepSeek provider")
        super().__init__(api_key=api_key, model=model, base_url=_DEEPSEEK_BASE_URL)
