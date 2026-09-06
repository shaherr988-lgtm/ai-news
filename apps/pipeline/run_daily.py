"""Daily pipeline entrypoint.

Usage:
    python -m apps.pipeline.run_daily              # fetch, summarize, embed, digest, email
    python -m apps.pipeline.run_daily --dry-run     # same, minus email + sent_at

Intended to be invoked once every 24 hours by an external scheduler (a Render
Cron Job in production, cron/APScheduler locally) — it does not schedule
itself, so it's safe to also just run by hand.
"""

import argparse
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from apps.agent.base import LLMProvider
from apps.agent.embedding_factory import get_embedding_provider
from apps.agent.factory import get_llm_provider
from apps.core.config import get_settings
from apps.core.db import SessionLocal
from apps.core.enums import SourceType
from apps.models.article import Article
from apps.models.digest import DailyDigest
from apps.models.source import Source
from apps.pipeline import curate, dedup, fetch_arxiv, fetch_blog, fetch_youtube
from apps.pipeline.call_budget import CallBudget
from apps.pipeline.digest_builder import build_digest
from apps.pipeline.mailer import get_email_sender
from apps.pipeline.summarize import summarize_articles
from apps.pipeline.time_window import utc_day_start
from apps.rag.embed_pipeline import embed_articles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Maps each SourceType to the *module* (not the bound function) that fetches
# it, so callers always go through `module.fetch_new_items(...)` — this keeps
# monkeypatching a fetcher module's fetch_new_items in tests (or swapping the
# implementation at runtime) working, unlike binding function objects at
# import time into a dict would.
_FETCHER_MODULES = {
    SourceType.YOUTUBE: fetch_youtube,
    SourceType.BLOG: fetch_blog,
    SourceType.ARXIV: fetch_arxiv,
}


def _fetch_new_articles(db, today_start: datetime, provider: LLMProvider, budget: CallBudget) -> int:
    """Step A. Returns the number of new articles inserted.

    Each source is fetched "since it was last fetched" (source.last_fetched_at),
    not a fixed rolling-hours window — a run always returns exactly what's new
    since last time, whatever that count happens to be. A source with no
    last_fetched_at yet (first run) uses `today_start` instead of its full feed
    history, so e.g. a blog RSS feed that returns its entire archive doesn't
    flood the first digest.

    A source whose new-item count exceeds curate.MAX_ITEMS_PER_SOURCE is
    additionally curated down to the most important ones (arXiv's daily
    category feeds routinely carry 300+ papers with the same timestamp) —
    the rest are simply not inserted; they were never new content the user
    couldn't also find by visiting the source directly.

    Commits once per source (not once for the whole batch): a bad row from one
    source (a too-long title, a blank url) must not roll back — and therefore
    drop — every other source's fresh articles for the day.
    """
    sources = db.query(Source).filter_by(is_active=True).all()
    inserted = 0

    for source in sources:
        fetcher_module = _FETCHER_MODULES.get(source.source_type)
        if fetcher_module is None:
            logger.warning("No fetcher for source_type=%s (source id=%s)", source.source_type, source.id)
            continue

        cutoff = source.last_fetched_at or today_start
        try:
            raw_items = fetcher_module.fetch_new_items(source, cutoff=cutoff)
        except Exception:
            logger.exception("Failed to fetch source id=%s name=%s", source.id, source.name)
            continue

        existing_external_ids, existing_urls = dedup.get_existing_keys(db, source.id)
        new_items = dedup.filter_new_items(
            raw_items, existing_external_ids=existing_external_ids, existing_urls=existing_urls
        )

        if len(new_items) > curate.MAX_ITEMS_PER_SOURCE:
            new_items = curate.select_most_important(provider, new_items, budget=budget)

        for item in new_items:
            article = dedup.to_article(source, item)
            if source.source_type == SourceType.YOUTUBE and item.external_id:
                # Only for genuinely-new videos (post-dedup) — never re-pay for
                # a transcript fetch on an item we've already stored.
                transcript = fetch_youtube.fetch_transcript(item.external_id)
                if transcript:
                    article.content = transcript
            db.add(article)

        source.last_fetched_at = datetime.now(timezone.utc)

        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception(
                "Failed to save new articles for source id=%s name=%s — skipping this source for this run",
                source.id,
                source.name,
            )
            continue

        inserted += len(new_items)

    logger.info("Step A: fetched %d new article(s) from %d active source(s)", inserted, len(sources))
    return inserted


def main(dry_run: bool = False) -> None:
    settings = get_settings()
    db = SessionLocal()

    try:
        # UTC, not the server's local calendar day — every cutoff computed
        # below is UTC-based, and mixing local "today" with a UTC cutoff
        # causes digests to mislabel articles near midnight.
        now = datetime.now(timezone.utc)
        today = now.date()
        today_start = utc_day_start(now)

        # Idempotency guard: never send the same day's digest twice.
        existing_digest = db.query(DailyDigest).filter_by(digest_date=today).first()
        if existing_digest and existing_digest.is_sent:
            logger.info("Digest for %s already sent at %s — exiting.", today, existing_digest.sent_at)
            return

        provider = get_llm_provider(settings)
        budget = CallBudget(settings.llm_daily_call_budget)

        # Step A — fetch new content from every active source.
        _fetch_new_articles(db, today_start, provider, budget)

        # Step B — summarize any article that doesn't have a summary yet.
        unsummarized = db.query(Article).filter(Article.summary.is_(None)).all()
        summarized_count = summarize_articles(db, provider, unsummarized, budget=budget)
        logger.info("Step B: summarized %d article(s)", summarized_count)

        # Step E — chunk + embed any article that hasn't been embedded yet,
        # so RAG chat (/chat) can answer questions about it. Runs right after
        # summarization since embedding prefers the summary as a fallback
        # when full content isn't available (see build_chunk_source_text).
        embedding_provider = get_embedding_provider(settings)
        unembedded = db.query(Article).filter(Article.embedded_at.is_(None)).all()
        embedded_count = embed_articles(
            db,
            embedding_provider,
            unembedded,
            chunk_size=settings.rag_chunk_size_chars,
            overlap=settings.rag_chunk_overlap_chars,
        )
        logger.info("Step E: embedded %d article(s)", embedded_count)

        # Step C — build today's digest from articles published since today_start.
        todays_articles = (
            db.query(Article)
            .options(joinedload(Article.source))
            .filter(Article.published_at >= today_start)
            .all()
        )
        digest_html = build_digest(provider, todays_articles, budget=budget)

        digest_row = existing_digest or DailyDigest(digest_date=today)
        digest_row.summary_text = digest_html
        digest_row.article_count = len(todays_articles)
        db.add(digest_row)
        db.commit()
        logger.info("Step C: built digest for %s with %d article(s)", today, len(todays_articles))

        # Step D — email it, unless this is a dry run.
        if dry_run:
            logger.info("Dry run: skipping email send. Digest preview:\n%s", digest_html)
            return

        if not settings.digest_recipient_email:
            logger.warning("DIGEST_RECIPIENT_EMAIL is not set — skipping send.")
            return

        sender = get_email_sender(settings)
        sender.send(
            to=settings.digest_recipient_email,
            subject=f"ملخص أخبار الذكاء الاصطناعي — {today.isoformat()}",
            html_body=digest_html,
        )
        digest_row.sent_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Step D: digest emailed to %s", settings.digest_recipient_email)

    finally:
        db.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the daily AI news digest pipeline once.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run fetch/summarize/build steps but do not send an email or mark the digest as sent.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main(dry_run=args.dry_run)
