"""Step E of the daily pipeline: chunk + embed every Article that hasn't
been embedded yet. Same idempotent, skip-and-log-on-failure pattern as
apps/pipeline/summarize.py.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from apps.agent.embedding_base import EmbeddingProvider
from apps.models.article import Article
from apps.models.chunk import ArticleChunk
from apps.rag.chunking import build_chunk_source_text, chunk_text

logger = logging.getLogger(__name__)


def embed_articles(
    db: Session,
    embedding_provider: EmbeddingProvider,
    articles: list[Article],
    *,
    chunk_size: int,
    overlap: int,
) -> int:
    """Chunk + embed each given article and commit. Returns the number of
    articles embedded (an article with no chunkable text is still marked
    embedded, so it isn't retried forever)."""
    embedded = 0
    for article in articles:
        try:
            source_text = build_chunk_source_text(article.title, article.content, article.summary)
            chunks = chunk_text(source_text, chunk_size=chunk_size, overlap=overlap)

            if chunks:
                vectors = embedding_provider.embed_documents([c.text for c in chunks])
                for chunk, vector in zip(chunks, vectors):
                    db.add(
                        ArticleChunk(
                            article_id=article.id,
                            chunk_index=chunk.index,
                            content=chunk.text,
                            embedding=vector,
                        )
                    )

            article.embedded_at = datetime.now(timezone.utc)
            embedded += 1
        except Exception:
            logger.exception("Failed to embed article id=%s url=%s", article.id, article.url)
            continue

    db.commit()
    return embedded
