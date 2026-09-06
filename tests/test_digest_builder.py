from datetime import datetime, timezone

from apps.agent.base import LLMProvider
from apps.core.enums import SourceType
from apps.models.article import Article
from apps.models.source import Source
from apps.pipeline.call_budget import CallBudget
from apps.pipeline.digest_builder import build_digest, group_by_source


class FailingProvider(LLMProvider):
    """Stub provider whose generate() always raises — for fallback tests."""

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        raise RuntimeError("should not be called")

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        raise RuntimeError("boom")


class FakeProvider(LLMProvider):
    """Stub provider — returns a canned string instead of calling any real API."""

    def __init__(self):
        self.last_prompt: str | None = None

    def summarize(self, system_prompt: str, content: str, *, max_tokens: int = 300) -> str:
        return "stub summary"

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 2000) -> str:
        self.last_prompt = user_prompt
        return "<p>stub digest</p>"


def _article(source: Source, title: str, url: str) -> Article:
    article = Article(
        title=title,
        url=url,
        summary=f"summary of {title}",
        published_at=datetime.now(timezone.utc),
    )
    article.source = source  # transient association, no DB needed
    return article


def test_group_by_source_groups_correctly():
    source_a = Source(name="Source A", source_type=SourceType.BLOG, url="https://a.example")
    source_b = Source(name="Source B", source_type=SourceType.YOUTUBE, url="https://b.example")

    articles = [
        _article(source_a, "A1", "https://a.example/1"),
        _article(source_b, "B1", "https://b.example/1"),
        _article(source_a, "A2", "https://a.example/2"),
    ]

    grouped = group_by_source(articles)

    assert set(grouped.keys()) == {"Source A", "Source B"}
    assert len(grouped["Source A"]) == 2
    assert len(grouped["Source B"]) == 1


def test_build_digest_returns_placeholder_when_no_articles():
    result = build_digest(FakeProvider(), [])
    assert "لا توجد أخبار جديدة" in result


def test_build_digest_calls_provider_and_includes_links_in_prompt():
    source = Source(name="Source A", source_type=SourceType.BLOG, url="https://a.example")
    articles = [_article(source, "A1", "https://a.example/1")]
    provider = FakeProvider()

    result = build_digest(provider, articles)

    assert result == "<p>stub digest</p>"
    assert "https://a.example/1" in provider.last_prompt
    assert "Source A" in provider.last_prompt


def test_build_digest_falls_back_to_plain_digest_when_budget_exhausted():
    source = Source(name="Source A", source_type=SourceType.BLOG, url="https://a.example")
    articles = [_article(source, "A1", "https://a.example/1")]
    provider = FakeProvider()
    budget = CallBudget(total=0)

    result = build_digest(provider, articles, budget=budget)

    assert provider.last_prompt is None  # generate() was never called
    assert "https://a.example/1" in result
    assert "A1" in result


def test_build_digest_falls_back_to_plain_digest_when_llm_call_fails():
    source = Source(name="Source A", source_type=SourceType.BLOG, url="https://a.example")
    articles = [_article(source, "A1", "https://a.example/1")]

    result = build_digest(FailingProvider(), articles)

    assert "https://a.example/1" in result
    assert "A1" in result
