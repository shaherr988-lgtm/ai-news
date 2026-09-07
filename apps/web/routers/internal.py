"""HTTP triggers for the daily pipeline, for a free external cron service
(e.g. cron-job.org) to call once a day — Render's own Cron Job service has
no free tier. Gated by RUN_DAILY_TOKEN, not HTTP Basic Auth (see the
exemption in apps/web/main.py): an external scheduler can't easily send
Basic Auth credentials, so a long random token in the URL is the auth
mechanism for these routes instead.
"""

import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from apps.core.config import get_settings
from apps.core.db import SessionLocal
from apps.models.digest import DailyDigest
from apps.pipeline.run_daily import main as run_daily_main

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_valid_token(token: str) -> None:
    settings = get_settings()
    if not settings.run_daily_token or not secrets.compare_digest(token, settings.run_daily_token):
        raise HTTPException(status_code=404)  # 404, not 401 — don't confirm the route even exists


@router.post("/run-daily")
def trigger_run_daily(background_tasks: BackgroundTasks, token: str = Query(...)):
    _require_valid_token(token)
    background_tasks.add_task(_run_safely)
    return {"status": "started"}


@router.post("/reset-today-digest")
def reset_today_digest(token: str = Query(...)):
    """Clears today's digest sent_at so the next /run-daily call actually
    re-sends the email — e.g. after changing DIGEST_RECIPIENT_EMAIL, since
    run_daily's idempotency guard otherwise skips a day already marked sent."""
    _require_valid_token(token)

    today = datetime.now(timezone.utc).date()
    db = SessionLocal()
    try:
        digest = db.query(DailyDigest).filter_by(digest_date=today).first()
        if digest is None:
            return {"status": "no digest found for today"}
        digest.sent_at = None
        db.commit()
        return {"status": "reset"}
    finally:
        db.close()


def _run_safely() -> None:
    try:
        run_daily_main(dry_run=False)
    except Exception:
        logger.exception("run_daily failed when triggered via /internal/run-daily")
