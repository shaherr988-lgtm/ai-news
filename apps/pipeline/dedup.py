"""Duplicate-prevention logic.

Split into a pure, DB-free core (easy to unit test) and a thin DB-backed
wrapper the pipeline actually calls. Dedup priority: external_id first (more
robust — e.g. a YouTube video ID is stable even if the URL gains query
params), falling back to (source_id, url).
"""

from typing import Iterable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.models.article import Article
from apps.models.source import Source


class _Item(Protocol):
    external_id: str | None
    title: str
    url: str
    content: str | None
    published_at: object


def filter_new_items(
    items: Iterable[_Item],
    *,
    existing_external_ids: set[str],
    existing_urls: set[str],
) -> list[_Item]:
    """Pure function: given items and the *already-known* keys for this source,
    return only the items that are genuinely new.

    - If an item has an external_id and it's in existing_external_ids -> duplicate.
    - Otherwise, if its url is in existing_urls -> duplicate.
    - Otherwise it's new.
    """
    new_items: list[_Item] = []
    seen_external_ids: set[str] = set()
    seen_urls: set[str] = set()

    for item in items:
        if item.external_id and (
            item.external_id in existing_external_ids or item.external_id in seen_external_ids
        ):
            continue
        if item.url in existing_urls or item.url in seen_urls:
            continue

        new_items.append(item)
        if item.external_id:
            seen_external_ids.add(item.external_id)
        seen_urls.add(item.url)

    return new_items


def get_existing_keys(db: Session, source_id: int) -> tuple[set[str], set[str]]:
    """DB-backed: fetch the external_ids and urls we already have for this source."""
    rows = db.execute(
        select(Article.external_id, Article.url).where(Article.source_id == source_id)
    ).all()
    existing_external_ids = {row[0] for row in rows if row[0]}
    existing_urls = {row[1] for row in rows}
    return existing_external_ids, existing_urls


def to_article(source: Source, item: _Item) -> Article:
    """Build a new (unsaved) Article ORM instance from a fetched item."""
    return Article(
        source_id=source.id,
        external_id=item.external_id,
        title=item.title,
        url=item.url,
        content=item.content,
        published_at=item.published_at,
    )
