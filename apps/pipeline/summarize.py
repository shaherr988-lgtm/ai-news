"""Step B: generate a per-item summary for every Article that doesn't have one yet."""

import logging

from sqlalchemy.orm import Session

from apps.agent.base import LLMProvider
from apps.agent.prompts import INSIGHTS_SYSTEM_PROMPT, build_item_summary_prompt
from apps.models.article import Article
from apps.pipeline.call_budget import CallBudget

logger = logging.getLogger(__name__)


def summarize_articles(
    db: Session, provider: LLMProvider, articles: list[Article], *, budget: CallBudget | None = None
) -> int:
    """Summarize each article in place and commit. Returns the number summarized.

    Failures on individual items are logged and skipped (left unsummarized for
    the next run) rather than aborting the whole batch. If `budget` is given
    and runs out (e.g. Gemini's free-tier daily cap), the loop stops rather
    than raising — the remaining articles just show their title instead of a
    summary in today's digest (see agent/prompts.build_digest_prompt), and get
    retried whenever a future run has budget again.
    """
    summarized = 0
    for article in articles:
        if budget is not None and not budget.spend():
            logger.info(
                "LLM call budget exhausted — leaving %d article(s) unsummarized this run",
                len(articles) - summarized,
            )
            break
        try:
            prompt = build_item_summary_prompt(article.title, article.content or "")
            article.summary = provider.summarize(INSIGHTS_SYSTEM_PROMPT, prompt)
            summarized += 1
        except Exception:
            logger.exception("Failed to summarize article id=%s url=%s", article.id, article.url)
            continue

    db.commit()
    return summarized
