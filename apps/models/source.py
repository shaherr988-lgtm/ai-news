from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.enums import SourceType
from apps.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from apps.models.article import Article


class Source(Base, TimestampMixin):
    """A YouTube channel or blog we pull content from."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)

    # For a blog: the site/article-listing URL to scrape.
    # For a YouTube channel: the channel's canonical URL (informational).
    url: Mapped[str] = mapped_column(String(1024), nullable=False)

    # For a YouTube channel: the per-channel RSS feed URL used for fetching.
    # e.g. https://www.youtube.com/feeds/videos.xml?channel_id=<ID>
    rss_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    articles: Mapped[list["Article"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Source id={self.id} name={self.name!r} type={self.source_type}>"
