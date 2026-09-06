from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Provider-agnostic interface for LLM calls used by the pipeline.

    Concrete implementations wrap a specific vendor SDK (OpenAI, Anthropic, ...).
    Nothing outside apps/agent/ should import a vendor SDK directly — always go
    through get_llm_provider() so the provider stays swappable via .env.
    """

    @abstractmethod
    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        """Return a short summary of a single article/video's content."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        """General-purpose completion, used to assemble the full daily digest
        from many already-summarized items."""
        raise NotImplementedError
