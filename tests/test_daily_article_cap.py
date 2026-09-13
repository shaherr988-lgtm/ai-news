"""Verifies max_articles_per_day is a hard ceiling across ALL sources
combined in apps/pipeline/run_daily.py's _fetch_new_articles — not just a
per-source limit (see curate.MAX_ITEMS_PER_SOURCE for that). Added after a
fresh/re-seeded database backfilled every source's full history in one run,
generating enough back-to-back LLM calls to trip transient Gemini failures."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.core.enums import SourceType
from apps.models import Base
from apps.models.source import Source
from apps.pipeline import fetch_blog, run_daily
from apps.pipeline.call_budget import CallBudget
from apps.pipeline.fetched_item import FetchedItem


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, future=True)()
    yield session
    session.close()
    engine.dispose()


class _FakeProvider:
    """Always picks the first N items when curation is invoked."""

    def generate(self, system_prompt, user_prompt, *, max_tokens=200):
        return "1, 2"

    def summarize(self, system_prompt, content, *, max_tokens=300):
        raise AssertionError("not used by this test")


def _fake_items(count: int, prefix: str) -> list[FetchedItem]:
    now = datetime.now(timezone.utc)
    return [
        FetchedItem(
            external_id=f"{prefix}-{i}",
            title=f"{prefix} item {i}",
            url=f"https://example.com/{prefix}/{i}",
            content="content",
            published_at=now,
        )
        for i in range(count)
    ]


def test_caps_total_inserted_articles_across_all_sources(monkeypatch, db_session):
    source_a = Source(name="Blog A", source_type=SourceType.BLOG, url="https://a.example.com")
    source_b = Source(name="Blog B", source_type=SourceType.BLOG, url="https://b.example.com")
    db_session.add_all([source_a, source_b])
    db_session.commit()

    # Each source has 8 new items (under curate.MAX_ITEMS_PER_SOURCE=10 on its
    # own), but combined (16) exceeds a max_articles_per_day of 10.
    items_by_source = {source_a.id: _fake_items(8, "a"), source_b.id: _fake_items(8, "b")}
    monkeypatch.setattr(
        fetch_blog, "fetch_new_items", lambda source, cutoff: items_by_source[source.id]
    )

    inserted = run_daily._fetch_new_articles(
        db_session,
        today_start=datetime.now(timezone.utc),
        provider=_FakeProvider(),
        budget=CallBudget(total=1000),
        max_articles_per_day=10,
    )

    assert inserted == 10
