from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.config import get_settings
from apps.models.base import Base

if TYPE_CHECKING:
    from apps.models.article import Article

_settings = get_settings()


class ArticleChunk(Base):
    """A retrievable slice of an Article's text, with its embedding vector.

    Populated by apps/rag/embed_pipeline.py (Step E of the daily pipeline) and
    read by apps/rag/retrieval.py for RAG chat. The embedding column's size is
    fixed at table-creation time to settings.embedding_dim — see the note in
    apps/core/config.py if you ever change EMBEDDING_PROVIDER.
    """

    __tablename__ = "article_chunks"
    __table_args__ = (
        UniqueConstraint("article_id", "chunk_index", name="uq_chunk_article_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(_settings.embedding_dim), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    article: Mapped["Article"] = relationship(back_populates="chunks")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ArticleChunk id={self.id} article_id={self.article_id} index={self.chunk_index}>"
