"""DB-backed retrieval for RAG chat: embed the question, find the most
similar chunks via pgvector, return them with their source Article for
citation. Requires a real pgvector-enabled Postgres — see apps/rag/similarity.py
for the DB-free unit-tested version of the ranking logic itself.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from apps.agent.embedding_base import EmbeddingProvider
from apps.models.article import Article
from apps.models.chunk import ArticleChunk


@dataclass
class RetrievedChunk:
    chunk: ArticleChunk
    article: Article
    score: float  # cosine similarity, higher = more relevant


def retrieve_top_k(
    db: Session, embedding_provider: EmbeddingProvider, question: str, *, k: int = 5
) -> list[RetrievedChunk]:
    """Embed `question` and return the k most similar chunks with their
    source Article, using pgvector's cosine-distance operator server-side."""
    query_vector = embedding_provider.embed_query(question)

    rows = (
        db.query(ArticleChunk, ArticleChunk.embedding.cosine_distance(query_vector).label("distance"))
        .options(joinedload(ArticleChunk.article))
        .order_by("distance")
        .limit(k)
        .all()
    )
    return [
        RetrievedChunk(chunk=chunk, article=chunk.article, score=1 - distance)
        for chunk, distance in rows
    ]
