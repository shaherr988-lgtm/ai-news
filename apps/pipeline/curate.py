"""Rank freshly-fetched items by importance and keep only the most relevant.

Needed for high-volume sources — arXiv's daily category feeds (cs.LG, cs.AI)
can legitimately carry 300+ papers announced with the same timestamp on a
single day. Summarizing every one of them would be expensive, slow, and
would drown out the rest of the digest. Only invoked when a source's new-item
count for the run exceeds MAX_ITEMS_PER_SOURCE — low-volume sources (a
YouTube channel, a blog) almost never hit it, so this costs nothing for them.

The excluded items are simply not inserted (not summarized, not in the
digest) — the user can still visit the source directly for anything skipped.
"""

import logging
import re

from apps.agent.base import LLMProvider
from apps.pipeline.call_budget import CallBudget
from apps.pipeline.fetched_item import FetchedItem

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_SOURCE = 10

CURATION_SYSTEM_PROMPT = """\
أنت محرر يختار أهم العناوين من قائمة أخبار/أوراق بحثية بمجال الذكاء الاصطناعي \
ليوم واحد. رتّب حسب الأهمية الفعلية والتأثير والجدة الحقيقية، لا حسب الترتيب \
المعطى. أعد فقط أرقام العناصر المختارة مفصولة بفواصل (مثال: 3, 1, 7)، من \
الأهم للأقل أهمية، بدون أي شرح أو نص إضافي.
"""


def _build_prompt(items: list[FetchedItem], keep: int) -> str:
    lines = [f"اختر أهم {keep} عنصر من أصل {len(items)}:", ""]
    for i, item in enumerate(items, start=1):
        snippet = (item.content or "")[:300].replace("\n", " ")
        lines.append(f"{i}. {item.title}\n   {snippet}")
    return "\n".join(lines)


def select_most_important(
    provider: LLMProvider,
    items: list[FetchedItem],
    *,
    keep: int = MAX_ITEMS_PER_SOURCE,
    budget: CallBudget | None = None,
) -> list[FetchedItem]:
    """Return at most `keep` items, chosen by the LLM as the most important.
    Falls back to the first `keep` items (original feed order) if the model's
    response can't be parsed into enough valid indices, or if `budget` is
    given and has no calls left (e.g. Gemini's free-tier daily cap) — the
    fetch/dedup work already done isn't worth losing over a ranking call."""
    if len(items) <= keep:
        return items

    if budget is not None and not budget.spend():
        logger.info("LLM call budget exhausted — curating by feed order instead of ranking")
        return items[:keep]

    try:
        response = provider.generate(CURATION_SYSTEM_PROMPT, _build_prompt(items, keep), max_tokens=200)
        indices = [int(n) for n in re.findall(r"\d+", response)]
    except Exception:
        logger.exception("Curation LLM call failed — falling back to feed order")
        return items[:keep]

    selected: list[FetchedItem] = []
    seen_positions: set[int] = set()
    for i in indices:
        if 1 <= i <= len(items) and i not in seen_positions:
            selected.append(items[i - 1])
            seen_positions.add(i)
        if len(selected) == keep:
            break

    if len(selected) < keep:
        for position, item in enumerate(items, start=1):
            if position in seen_positions:
                continue
            selected.append(item)
            if len(selected) == keep:
                break

    return selected
