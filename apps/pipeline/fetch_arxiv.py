"""Fetch new papers for an arXiv Source via its category RSS/Atom feed.

Each arXiv category publishes a public feed at:
https://rss.arxiv.org/rss/<category>   (e.g. cs.LG, cs.AI, cs.CL)

Same shape as fetch_youtube.py — a Source's `rss_url` holds the feed URL.
"""

from datetime import datetime

import feedparser

from apps.models.source import Source
from apps.pipeline.fetched_item import FetchedItem
from apps.pipeline.time_window import entry_published_at, is_recent_enough


def fetch_new_items(source: Source, *, cutoff: datetime) -> list[FetchedItem]:
    """Return papers from `source`'s arXiv feed published since `cutoff`."""
    feed_url = source.rss_url or source.url
    if not feed_url:
        return []

    parsed = feedparser.parse(feed_url)

    items: list[FetchedItem] = []
    for entry in parsed.entries:
        published_at = entry_published_at(entry)
        if published_at is None or not is_recent_enough(published_at, cutoff):
            continue

        # arXiv's entry.id is a stable per-paper URL (e.g. arxiv.org/abs/2401.01234) —
        # a good dedup key even if the feed later reorders or updates an entry.
        arxiv_id = getattr(entry, "id", None)
        link = getattr(entry, "link", None) or arxiv_id
        if not link:
            continue  # no usable identifier at all - skip rather than insert a blank url
        title = " ".join(getattr(entry, "title", "(untitled)").split())  # collapse newlines/whitespace
        summary = getattr(entry, "summary", None)

        items.append(
            FetchedItem(
                external_id=arxiv_id,
                title=title,
                url=link,
                content=summary,
                published_at=published_at,
            )
        )
    return items
