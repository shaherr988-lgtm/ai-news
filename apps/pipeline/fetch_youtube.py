"""Fetch new videos for a YouTube Source via its channel RSS feed.

No YouTube Data API key needed — every channel publishes a public RSS feed at
https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
"""

import re
from datetime import datetime

import feedparser
import requests

from apps.models.source import Source
from apps.pipeline.fetched_item import FetchedItem
from apps.pipeline.time_window import entry_published_at, is_recent_enough

_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Tried in order against a channel page's HTML. The canonical <link> is the
# most stable — YouTube's inline-JSON key names have drifted before.
_CHANNEL_ID_PATTERNS = [
    re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"'),
    re.compile(r'"externalId":"(UC[\w-]{22})"'),
    re.compile(r'"channelId":"(UC[\w-]{22})"'),
]


def resolve_channel_id(channel_url: str) -> str:
    """Fetch a channel's page (by @handle or /channel/ URL) and extract its
    stable channel_id, for building the RSS feed URL at seed time."""
    response = requests.get(channel_url, timeout=15, headers={"User-Agent": _BROWSER_USER_AGENT})
    response.raise_for_status()
    for pattern in _CHANNEL_ID_PATTERNS:
        match = pattern.search(response.text)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract a channel_id from {channel_url}")


def rss_url_for_channel(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def fetch_new_items(source: Source, *, cutoff: datetime) -> list[FetchedItem]:
    """Return videos from `source`'s RSS feed published since `cutoff`.

    Content here is just the RSS description — the daily pipeline enriches it
    with the full video transcript (fetch_transcript, below) only for items
    that also survive dedup, so we never pay for a transcript fetch twice.
    """
    feed_url = source.rss_url or source.url
    if not feed_url:
        return []

    parsed = feedparser.parse(feed_url)

    items: list[FetchedItem] = []
    for entry in parsed.entries:
        link = getattr(entry, "link", "")
        if "/shorts/" in link:
            continue

        published_at = entry_published_at(entry)
        if published_at is None or not is_recent_enough(published_at, cutoff):
            continue

        video_id = getattr(entry, "yt_videoid", None) or getattr(entry, "id", None)
        summary = getattr(entry, "summary", None)

        items.append(
            FetchedItem(
                external_id=video_id,
                title=getattr(entry, "title", "(untitled)"),
                url=link,
                content=summary,
                published_at=published_at,
            )
        )
    return items


def fetch_transcript(video_id: str) -> str | None:
    """Best-effort full video transcript, richer input for summarization than
    YouTube's short RSS description. Returns None quietly on any failure
    (captions disabled, no transcript available, or — commonly, when running
    from a datacenter IP such as Render's — YouTube blocking the request
    without a residential proxy configured via PROXY_USERNAME/PROXY_PASSWORD);
    callers fall back to the RSS description in that case.
    """
    import os

    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
    from youtube_transcript_api.proxies import WebshareProxyConfig

    proxy_username = os.getenv("PROXY_USERNAME")
    proxy_password = os.getenv("PROXY_PASSWORD")
    proxy_config = None
    if proxy_username and proxy_password:
        proxy_config = WebshareProxyConfig(proxy_username=proxy_username, proxy_password=proxy_password)

    try:
        api = YouTubeTranscriptApi(proxy_config=proxy_config)
        transcript = api.fetch(video_id)
        return " ".join(snippet.text for snippet in transcript.snippets)
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None
