from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-agnostic interface for turning text into vectors.

    Parallel to LLMProvider (apps/agent/base.py): nothing outside apps/agent/
    should import a vendor embeddings SDK directly — always go through
    get_embedding_provider() so the backend stays swappable via .env.

    embed_documents / embed_query are separate methods (even though today's
    only implementation treats them identically) because some providers
    (e.g. Voyage AI) use a different call for indexing vs. querying and it
    measurably improves retrieval quality — keeping the split now means
    adding such a provider later doesn't touch any caller.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of the vectors this provider returns — must match
        settings.embedding_dim, since the pgvector column size is fixed."""
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunks for storage."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single user question for retrieval."""
        raise NotImplementedError
