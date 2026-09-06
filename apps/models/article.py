from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.models.base import Base

if TYPE_CHECKING:
    from apps.models.chunk import ArticleChunk
    from apps.models.source import Source


class Article(Base):
    """A single piece of content pulled from a Source (a video or a blog post)."""

    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("source_id", "url", name="uq_article_source_url"),
        Index("ix_articles_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # YouTube video ID or another provider-native ID, when available. Preferred
    # dedup key over `url` because it's stable across URL query-param variations.
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Full text content (blog body) or description (YouTube). Nullable because
    # some YouTube RSS entries only carry a short description.
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Per-item LLM-generated short summary, populated during the daily pipeline.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Set once this article has been chunked + embedded for RAG chat (Step E).
    # Same idempotency pattern as `summary` — NULL means "still to do".
    embedded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source: Mapped["Source"] = relationship(back_populates="articles")
    chunks: Mapped[list["ArticleChunk"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )

    @property
    def is_summarized(self) -> bool:
        return self.summary is not None

    @property
    def is_embedded(self) -> bool:
        return self.embedded_at is not None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Article id={self.id} title={self.title!r}>"
