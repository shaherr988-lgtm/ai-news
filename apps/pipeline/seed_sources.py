"""Insert a starter set of placeholder Sources for AI/ML/CS education content.

Run with: python -m apps.pipeline.seed_sources

These are just examples to get the pipeline running end-to-end on day one.
Add/remove/edit sources any time from the /sources page in the web app —
you never need to touch this file again after the first run.
"""

from apps.core.db import SessionLocal
from apps.core.enums import SourceType
from apps.models.source import Source

SEED_BLOGS = [
    {"name": "OpenAI Blog", "url": "https://openai.com/news"},
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news"},
]

SEED_YOUTUBE_CHANNELS = [
    {"name": "Andrej Karpathy", "channel_id": "UCPk8m_r6fkUSYmvgCBwq-sw"},
    {"name": "StatQuest with Josh Starmer", "channel_id": "UCtYLUTtgS3k1Fg4y5tAhLbw"},
    {"name": "sentdex", "channel_id": "UCfzlCWGWYyIQ0aLC5w48gBQ"},
    {"name": "3Blue1Brown", "channel_id": "UCYO_jab_esuFRV4b17AJtAw"},
]

# arXiv category feeds — see https://info.arxiv.org/help/rss.html
SEED_ARXIV_CATEGORIES = [
    {"name": "arXiv cs.LG (Machine Learning)", "category": "cs.LG"},
    {"name": "arXiv cs.AI (Artificial Intelligence)", "category": "cs.AI"},
]


def seed() -> int:
    """Returns how many sources were newly added (0 if all were already present)."""
    db = SessionLocal()
    try:
        existing_names = {name for (name,) in db.query(Source.name).all()}

        added = 0
        for blog in SEED_BLOGS:
            if blog["name"] in existing_names:
                continue
            db.add(Source(name=blog["name"], source_type=SourceType.BLOG, url=blog["url"]))
            added += 1

        for channel in SEED_YOUTUBE_CHANNELS:
            if channel["name"] in existing_names:
                continue
            channel_url = f"https://www.youtube.com/channel/{channel['channel_id']}"
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['channel_id']}"
            db.add(
                Source(
                    name=channel["name"],
                    source_type=SourceType.YOUTUBE,
                    url=channel_url,
                    rss_url=rss_url,
                )
            )
            added += 1

        for category in SEED_ARXIV_CATEGORIES:
            if category["name"] in existing_names:
                continue
            feed_url = f"https://rss.arxiv.org/rss/{category['category']}"
            db.add(
                Source(
                    name=category["name"],
                    source_type=SourceType.ARXIV,
                    url=f"https://arxiv.org/list/{category['category']}/recent",
                    rss_url=feed_url,
                )
            )
            added += 1

        db.commit()
        print(f"Seeded {added} source(s) ({len(existing_names)} already present, skipped).")
        return added
    finally:
        db.close()


if __name__ == "__main__":
    seed()
