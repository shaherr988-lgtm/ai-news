"""Fetch new posts for a blog Source by scraping its listing page + each post page.

This is a generic, best-effort scraper: it looks for links that plausibly point
to individual posts, then reads title / published date / body text off each post
page using common HTML conventions (OpenGraph tags, <time> elements, <article>
containers). Blogs vary a lot in markup, so for a specific blog you may need to
tune SELECTORS below or write a source-specific override — this gets most
standard blog/news layouts (including OpenAI's and Anthropic's) out of the box.
"""

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from apps.models.source import Source
from apps.pipeline.fetched_item import FetchedItem
from apps.pipeline.time_window import is_recent_enough

REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "ai-news-aggregator/0.1 (+daily digest bot)"
MAX_POSTS_PER_RUN = 20


def _get(url: str) -> requests.Response | None:
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response
    except requests.RequestException:
        return None


def _discover_post_links(listing_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(listing_url).netloc
    links: list[str] = []
    seen: set[str] = set()

    # Prefer links inside <article> tags or headings, which is how most blog
    # index/listing pages mark up post teasers.
    candidates = soup.select("article a[href]") or soup.select("h1 a[href], h2 a[href], h3 a[href]")
    if not candidates:
        candidates = soup.select("a[href]")

    for a in candidates:
        href = a.get("href")
        if not href:
            continue
        absolute = urljoin(listing_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc != domain:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
        if len(links) >= MAX_POSTS_PER_RUN:
            break
    return links


def _parse_iso_datetime(raw: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    # A timestamp with no UTC offset must not be treated as the server's local
    # time zone (which is what comparing/using a naive datetime would do) —
    # assume UTC, same as every other source of published_at in this project.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_published_at(soup: BeautifulSoup) -> datetime | None:
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if meta and meta.get("content"):
        parsed = _parse_iso_datetime(meta["content"])
        if parsed is not None:
            return parsed

    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        parsed = _parse_iso_datetime(time_tag["datetime"])
        if parsed is not None:
            return parsed

    return None


def _extract_title(soup: BeautifulSoup) -> str:
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        return og_title["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "(untitled)"


def _extract_content(soup: BeautifulSoup) -> str | None:
    article = soup.find("article")
    container = article or soup.find(attrs={"class": lambda c: c and "content" in c.lower()}) or soup.body
    if not container:
        return None
    text = container.get_text(separator="\n", strip=True)
    return text[:20000] if text else None  # cap stored size


def fetch_new_items(source: Source, *, cutoff: datetime) -> list[FetchedItem]:
    """Return blog posts from `source`'s listing page published since `cutoff`."""
    listing = _get(source.url)
    if listing is None:
        return []

    post_links = _discover_post_links(source.url, listing.text)

    items: list[FetchedItem] = []
    for url in post_links:
        post_response = _get(url)
        if post_response is None:
            continue
        soup = BeautifulSoup(post_response.text, "html.parser")

        published_at = _extract_published_at(soup)
        if published_at is None:
            # No reliable date found — best-effort fallback so we don't silently
            # drop the post; treat it as published now (it will show up in
            # today's digest and not be re-fetched next run thanks to dedup).
            published_at = datetime.now(timezone.utc)
        elif not is_recent_enough(published_at, cutoff):
            continue

        items.append(
            FetchedItem(
                external_id=None,
                title=_extract_title(soup),
                url=url,
                content=_extract_content(soup),
                published_at=published_at,
            )
        )
    return items
