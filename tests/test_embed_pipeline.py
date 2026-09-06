from datetime import datetime, timezone

from apps.agent.embedding_base import EmbeddingProvider
from apps.core.enums import SourceType
from apps.models.article import Article
from apps.models.chunk import ArticleChunk
from apps.models.source import Source
from apps.rag.embed_pipeline import embed_articles


class FakeEmbeddingProvider(EmbeddingProvider):
    """Stub — returns a fixed-length fake vector per text, no real API call."""

    def __init__(self, dim: int = 8):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] * self._dim for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))] * self._dim


def _make_article(db_session, source: Source, content: str | None = "some body text") -> Article:
    article = Article(
        source_id=source.id,
        title="Test Article",
        url=f"https://example.com/{id(content)}",
        content=content,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(article)
    db_session.commit()
    return article


def test_embed_articles_creates_chunks_and_sets_embedded_at(db_session):
    source = Source(name="S", source_type=SourceType.BLOG, url="https://example.com")
    db_session.add(source)
    db_session.commit()
    article = _make_article(db_session, source, content="word " * 300)  # long enough to split

    embedded_count = embed_articles(
        db_session, FakeEmbeddingProvider(), [article], chunk_size=200, overlap=20
    )

    assert embedded_count == 1
    assert article.embedded_at is not None
    chunks = db_session.query(ArticleChunk).filter_by(article_id=article.id).all()
    assert len(chunks) > 1


def test_embed_articles_marks_embedded_even_with_no_chunkable_text(db_session):
    source = Source(name="S", source_type=SourceType.BLOG, url="https://example.com")
    db_session.add(source)
    db_session.commit()
    article = Article(
        source_id=source.id,
        title="",
        url="https://example.com/empty",
        content=None,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(article)
    db_session.commit()

    embedded_count = embed_articles(
        db_session, FakeEmbeddingProvider(), [article], chunk_size=200, overlap=20
    )

    assert embedded_count == 1
    assert article.embedded_at is not None
    assert db_session.query(ArticleChunk).filter_by(article_id=article.id).count() == 0


def test_embed_articles_skips_failing_article_without_aborting_batch(db_session, monkeypatch):
    source = Source(name="S", source_type=SourceType.BLOG, url="https://example.com")
    db_session.add(source)
    db_session.commit()
    good = _make_article(db_session, source, content="fine content")
    bad = _make_article(db_session, source, content="also fine content")

    provider = FakeEmbeddingProvider()
    original_embed_documents = provider.embed_documents
    call_count = {"n": 0}

    def flaky_embed_documents(texts):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated embedding API failure")
        return original_embed_documents(texts)

    monkeypatch.setattr(provider, "embed_documents", flaky_embed_documents)

    embedded_count = embed_articles(db_session, provider, [bad, good], chunk_size=200, overlap=20)

    assert embedded_count == 1  # only `good` succeeded
    assert good.embedded_at is not None
    assert bad.embedded_at is None
