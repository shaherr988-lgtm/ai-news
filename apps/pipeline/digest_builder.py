"""Step C: assemble the final daily digest HTML from today's summarized articles."""

import logging
from collections import defaultdict

import bleach

from apps.agent.base import LLMProvider
from apps.agent.prompts import INSIGHTS_SYSTEM_PROMPT, build_digest_prompt
from apps.models.article import Article
from apps.pipeline.call_budget import CallBudget

logger = logging.getLogger(__name__)

# The digest prompt embeds scraped article titles/summaries verbatim (see
# build_digest_prompt), so the LLM's HTML output is not trusted content — a
# source page containing an HTML/script snippet (accidentally, or via a
# deliberate prompt injection) could otherwise get reproduced into the digest
# and execute in the browser wherever it's rendered with `| safe`
# (digest_detail.html) or delivered as the email body. Allow only the
# formatting tags the prompt actually asks for.
_ALLOWED_TAGS = ["p", "h2", "h3", "ul", "ol", "li", "strong", "em", "a", "br"]
_ALLOWED_ATTRS = {"a": ["href", "title"]}


def sanitize_digest_html(html: str) -> str:
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


def group_by_source(articles: list[Article]) -> dict[str, list[Article]]:
    grouped: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        grouped[article.source.name].append(article)
    return dict(grouped)


def _deterministic_digest(articles: list[Article]) -> str:
    """No-LLM fallback: a plain grouped list (title + summary-or-title + link)
    with no AI-written narrative. Used when the LLM call can't run at all
    (budget exhausted) or fails for any other reason — a plain digest still
    beats losing an entire day's fetched-and-summarized work."""
    parts = ["<p>تعذّر توليد ملخص ذكي اليوم — هذا عرض مباشر للعناوين.</p>"]
    for source_name, source_articles in group_by_source(articles).items():
        parts.append(f"<h2>{source_name}</h2><ul>")
        for article in source_articles:
            text = article.summary or article.title
            parts.append(f'<li><a href="{article.url}">{article.title}</a> — {text}</li>')
        parts.append("</ul>")
    return "".join(parts)


def build_digest(
    provider: LLMProvider, articles: list[Article], *, budget: CallBudget | None = None
) -> str:
    """Return the digest body as sanitized HTML, ready to store in
    DailyDigest.summary_text and to send as the email body.

    Falls back to a plain, non-AI-written digest (_deterministic_digest) if
    `budget` has no calls left, or if the LLM call fails for any other reason
    (rate limit, network error, ...) — a whole day's fetching, curating, and
    summarizing must never be thrown away just because the very last call
    failed.
    """
    if not articles:
        return "<p>لا توجد أخبار جديدة اليوم.</p>"

    if budget is not None and not budget.spend_for_digest():
        logger.warning("LLM call budget exhausted — using plain digest instead of AI-written one")
        return sanitize_digest_html(_deterministic_digest(articles))

    grouped = group_by_source(articles)
    prompt = build_digest_prompt(grouped)
    try:
        raw_html = provider.generate(INSIGHTS_SYSTEM_PROMPT, prompt, max_tokens=2000)
    except Exception:
        logger.exception("Digest-build LLM call failed — using plain digest instead")
        return sanitize_digest_html(_deterministic_digest(articles))

    return sanitize_digest_html(raw_html)
