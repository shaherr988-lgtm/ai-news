"""Shared shape returned by every source fetcher (fetch_youtube/fetch_blog/fetch_arxiv).

Was previously defined identically in all three fetcher modules - consolidated here
so a future field change only needs to happen once.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class FetchedItem:
    external_id: str | None
    title: str
    url: str
    content: str | None
    published_at: datetime
