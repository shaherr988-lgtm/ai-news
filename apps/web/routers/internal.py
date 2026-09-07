"""HTTP trigger for the daily pipeline, for a free external cron service
(e.g. cron-job.org) to call once a day — Render's own Cron Job service has
no free tier. Gated by RUN_DAILY_TOKEN, not HTTP Basic Auth (see the
exemption in apps/web/main.py): an external scheduler can't easily send
Basic Auth credentials, so a long random token in the URL is the auth
mechanism for this one route instead.
"""

import logging
import secrets

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from apps.core.config import get_settings
from apps.pipeline.run_daily import main as run_daily_main

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/run-daily")
def trigger_run_daily(background_tasks: BackgroundTasks, token: str = Query(...)):
    settings = get_settings()
    if not settings.run_daily_token or not secrets.compare_digest(token, settings.run_daily_token):
        raise HTTPException(status_code=404)  # 404, not 401 — don't confirm the route even exists

    background_tasks.add_task(_run_safely)
    return {"status": "started"}


def _run_safely() -> None:
    try:
        run_daily_main(dry_run=False)
    except Exception:
        logger.exception("run_daily failed when triggered via /internal/run-daily")
