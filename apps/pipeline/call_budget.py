"""Per-run LLM call budget.

Some providers have a hard daily cap far below what a busy day's fetch can
need (Gemini's free tier: 20 generate_content calls/day total). Without this,
run_daily hits the cap mid-run and the whole pipeline crashes — including the
final digest-build call, which throws away a run's worth of already-fetched
and already-summarized work.

Not a persistent tracker across runs/days — just keeps one run honest against
LLM_DAILY_CALL_BUDGET, and always keeps one call in reserve for the digest
build so summarization/curation can never fully starve it.
"""


class CallBudget:
    def __init__(self, total: int, reserved_for_digest: int = 1):
        self._remaining = max(0, total)
        self._reserved = max(0, reserved_for_digest)

    def spend(self) -> bool:
        """For curation/summarization calls. Refuses once only the digest's
        reserved call is left, so those steps can never starve it."""
        if self._remaining <= self._reserved:
            return False
        self._remaining -= 1
        return True

    def spend_for_digest(self) -> bool:
        """For the final digest-build call — allowed to spend the reserve."""
        if self._remaining <= 0:
            return False
        self._remaining -= 1
        return True
