"""Step B: generate a per-item summary for every Article that doesn't have one yet."""

import logging
import time

from sqlalchemy.orm import Session

from apps.agent.base import LLMProvider
from apps.agent.prompts import INSIGHTS_SYSTEM_PROMPT, build_item_summary_prompt
from apps.models.article import Article
from apps.pipeline.call_budget import CallBudget

logger = logging.getLogger(__name__)


def summarize_articles(
    db: Session,
    provider: LLMProvider,
    articles: list[Article],
    *,
    budget: CallBudget | None = None,
    request_delay_seconds: float = 0,
) -> int:
    """Summarize each article in place, committing after every one. Returns
    the number summarized.

    Commits per-article (not once at the end) so a run interrupted partway
    through — a dropped DB connection, a killed background task — keeps
    whatever it already finished instead of losing all of it. A whole batch
    committed only at the end meant an interrupted run retried every article
    from scratch next time, burning more of Gemini's shared daily quota for
    no progress each time (confirmed cause of the 2026-09-15/16 outage).

    Failures on individual items are logged and skipped (left unsummarized for
    the next run) rather than aborting the whole batch. If `budget` is given
    and runs out (e.g. Gemini's free-tier daily cap), the loop stops rather
    than raising — the remaining articles just show their title instead of a
    summary in today's digest (see agent/prompts.build_digest_prompt), and get
    retried whenever a future run has budget again.

    `request_delay_seconds`: paused before each call (not just the first) to
    stay under the provider's per-minute rate limit — see llm_request_delay_seconds
    in apps/core/config.py for why a daily budget alone isn't enough.
    """
    summarized = 0
    for article in articles:
        if budget is not None and not budget.spend():
            logger.info(
                "LLM call budget exhausted — leaving %d article(s) unsummarized this run",
                len(articles) - summarized,
            )
            break
        if request_delay_seconds:
            time.sleep(request_delay_seconds)
        try:
            prompt = build_item_summary_prompt(article.title, article.content or "")
            article.summary = provider.summarize(INSIGHTS_SYSTEM_PROMPT, prompt)
            db.commit()
            summarized += 1
        except Exception:
            logger.exception("Failed to summarize article id=%s url=%s", article.id, article.url)
            db.rollback()
            continue

    return summarized
