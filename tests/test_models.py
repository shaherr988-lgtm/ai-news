from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from apps.core.enums import SourceType
from apps.models.article import Article
from apps.models.chunk import ArticleChunk
from apps.models.source import Source


def _make_source(db_session, name="Test Blog") -> Source:
    source = Source(name=name, source_type=SourceType.BLOG, url="https://example.com")
    db_session.add(source)
    db_session.commit()
    return source


def test_duplicate_source_url_raises_integrity_error(db_session):
    source = _make_source(db_session)
    now = datetime.now(timezone.utc)

    db_session.add(
        Article(source_id=source.id, title="First", url="https://example.com/post", published_at=now)
    )
    db_session.commit()

    db_session.add(
        Article(source_id=source.id, title="Dup", url="https://example.com/post", published_at=now)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_is_summarized_reflects_summary_column(db_session):
    source = _make_source(db_session)
    article = Article(
        source_id=source.id,
        title="No summary yet",
        url="https://example.com/a",
        published_at=datetime.now(timezone.utc),
    )
    assert article.is_summarized is False

    article.summary = "A short summary."
    assert article.is_summarized is True


def test_daily_digest_is_sent_reflects_sent_at():
    from apps.models.digest import DailyDigest
    from datetime import date

    digest = DailyDigest(digest_date=date.today(), summary_text="<p>hi</p>", article_count=0)
    assert digest.is_sent is False

    digest.sent_at = datetime.now(timezone.utc)
    assert digest.is_sent is True


def _make_article(db_session, source: Source, url="https://example.com/article") -> Article:
    article = Article(
        source_id=source.id, title="Some Article", url=url, published_at=datetime.now(timezone.utc)
    )
    db_session.add(article)
    db_session.commit()
    return article


def test_is_embedded_reflects_embedded_at_column(db_session):
    source = _make_source(db_session)
    article = _make_article(db_session, source)
    assert article.is_embedded is False

    article.embedded_at = datetime.now(timezone.utc)
    assert article.is_embedded is True


def test_article_chunk_insert_and_cascade_delete(db_session):
    source = _make_source(db_session)
    article = _make_article(db_session, source)

    db_session.add(
        ArticleChunk(article_id=article.id, chunk_index=0, content="first chunk", embedding=[0.1] * 1536)
    )
    db_session.add(
        ArticleChunk(article_id=article.id, chunk_index=1, content="second chunk", embedding=[0.2] * 1536)
    )
    db_session.commit()

    assert db_session.query(ArticleChunk).count() == 2

    db_session.delete(article)
    db_session.commit()

    # cascade="all, delete-orphan" on Article.chunks should remove them too.
    assert db_session.query(ArticleChunk).count() == 0


def test_duplicate_chunk_index_for_same_article_raises_integrity_error(db_session):
    source = _make_source(db_session)
    article = _make_article(db_session, source)

    db_session.add(
        ArticleChunk(article_id=article.id, chunk_index=0, content="a", embedding=[0.0] * 1536)
    )
    db_session.commit()

    db_session.add(
        ArticleChunk(article_id=article.id, chunk_index=0, content="b", embedding=[0.0] * 1536)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
