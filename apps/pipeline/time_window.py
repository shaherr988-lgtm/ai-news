"""Shared time-window helpers for feedparser-based fetchers (YouTube, arXiv).

Was previously reimplemented independently in each fetcher, which is how the
missing `updated_parsed` fallback ended up existing in only one of them.

Cutoff, not a rolling hour window: a fixed DIGEST_WINDOW_HOURS silently drops
genuinely-new items on a busy day and re-shows nothing on a quiet one. Instead
each source is fetched "since it was last fetched" (source.last_fetched_at),
so a run always returns exactly what's new since last time, whatever that
count happens to be. A source with no last_fetched_at yet (first run) uses
the start of the current UTC day as its cutoff instead of the full feed
history — see utc_day_start() and its call site in run_daily.py.
"""

from datetime import datetime, timezone


def entry_published_at(entry) -> datetime | None:
    """Best-effort publish time for a feedparser entry: prefers `published`,
    falls back to `updated` when a feed omits `published` for some items."""
    published_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if published_struct is None:
        return None
    return datetime(*published_struct[:6], tzinfo=timezone.utc)


def utc_day_start(moment: datetime | None = None) -> datetime:
    moment = moment or datetime.now(timezone.utc)
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def is_recent_enough(published_at: datetime, cutoff: datetime) -> bool:
    return published_at >= cutoff
