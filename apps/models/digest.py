from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from apps.models.base import Base


class DailyDigest(Base):
    """The generated daily digest — one row per calendar day."""

    __tablename__ = "daily_digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)

    # Rendered HTML body of the digest (also what gets emailed).
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # NULL until the email actually sends successfully — this is what makes
    # re-running the daily job idempotent (see apps/pipeline/run_daily.py).
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def is_sent(self) -> bool:
        return self.sent_at is not None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DailyDigest date={self.digest_date} sent={self.is_sent}>"
