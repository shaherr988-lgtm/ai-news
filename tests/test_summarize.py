from unittest.mock import MagicMock

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
    db.commit.assert_called_once()


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
