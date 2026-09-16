from unittest.mock import MagicMock, patch

from apps.agent.base import LLMProvider
from apps.models.article import Article
from apps.pipeline.call_budget import CallBudget
from apps.pipeline.summarize import summarize_articles


class FakeProvider(LLMProvider):
    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        return f"summary of: {content[:20]}"

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        raise NotImplementedError


def _article(title: str) -> Article:
    return Article(title=title, url=f"https://example.com/{title}", content=title)


def test_summarizes_every_article_when_no_budget_given():
    db = MagicMock()
    articles = [_article("A"), _article("B"), _article("C")]

    summarized = summarize_articles(db, FakeProvider(), articles)

    assert summarized == 3
    assert all(a.summary is not None for a in articles)
    assert db.commit.call_count == 3


class FlakyProvider(LLMProvider):
    """Fails on the 2nd article only — for interrupted-run tests."""

    def __init__(self):
        self.calls = 0

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("simulated interruption")
        return f"summary of: {content[:20]}"

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        raise NotImplementedError


def test_earlier_progress_survives_a_later_failure():
    db = MagicMock()
    articles = [_article("A"), _article("B"), _article("C")]

    summarized = summarize_articles(db, FlakyProvider(), articles)

    assert summarized == 2
    assert articles[0].summary is not None  # committed before the failure
    assert articles[1].summary is None  # failed, left for next run
    assert articles[2].summary is not None  # continued after the failure
    assert db.commit.call_count == 2
    db.rollback.assert_called_once()


def test_stops_early_once_budget_is_exhausted():
    db = MagicMock()
    articles = [_article("A"), _article("B"), _article("C")]
    budget = CallBudget(total=2, reserved_for_digest=0)

    summarized = summarize_articles(db, FakeProvider(), articles, budget=budget)

    assert summarized == 2
    assert articles[0].summary is not None
    assert articles[1].summary is not None
    assert articles[2].summary is None  # left for a future run


def test_zero_budget_summarizes_nothing():
    db = MagicMock()
    articles = [_article("A")]
    budget = CallBudget(total=0)

    summarized = summarize_articles(db, FakeProvider(), articles, budget=budget)

    assert summarized == 0
    assert articles[0].summary is None


def test_no_delay_by_default():
    db = MagicMock()
    articles = [_article("A"), _article("B")]

    with patch("apps.pipeline.summarize.time.sleep") as mock_sleep:
        summarize_articles(db, FakeProvider(), articles)

    mock_sleep.assert_not_called()


def test_sleeps_before_each_call_when_delay_configured():
    db = MagicMock()
    articles = [_article("A"), _article("B"), _article("C")]

    with patch("apps.pipeline.summarize.time.sleep") as mock_sleep:
        summarize_articles(db, FakeProvider(), articles, request_delay_seconds=30)

    assert mock_sleep.call_count == 3
    mock_sleep.assert_called_with(30)


def test_no_sleep_for_articles_skipped_by_exhausted_budget():
    db = MagicMock()
    articles = [_article("A"), _article("B"), _article("C")]
    budget = CallBudget(total=1, reserved_for_digest=0)

    with patch("apps.pipeline.summarize.time.sleep") as mock_sleep:
        summarize_articles(db, FakeProvider(), articles, budget=budget, request_delay_seconds=30)

    # Only the one article actually summarized before budget ran out sleeps.
    assert mock_sleep.call_count == 1
