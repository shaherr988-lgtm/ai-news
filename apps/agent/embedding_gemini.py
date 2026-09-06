from google import genai
from google.genai import types

from apps.agent.embedding_base import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Free-tier-friendly alternative to OpenAI for embeddings — an
    aistudio.google.com API key works without adding billing, unlike OpenAI."""

    def __init__(self, api_key: str, model: str = "gemini-embedding-001", dimension: int = 768):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required to use the Gemini embedding provider")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        response = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self._dimension,
            ),
        )
        return [embedding.values for embedding in response.embeddings]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]
