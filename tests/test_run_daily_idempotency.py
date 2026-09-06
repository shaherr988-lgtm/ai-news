"""Verifies the idempotency guard in apps/pipeline/run_daily.py: if today's
DailyDigest already has sent_at set, main() must exit before touching the LLM
provider or the email sender."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.core.config import Settings
from apps.models import Base
from apps.models.digest import DailyDigest
from apps.pipeline import run_daily


@pytest.fixture()
def sqlite_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, future=True)
    engine.dispose()


def test_skips_send_when_already_sent_today(monkeypatch, sqlite_session_factory):
    # Seed: today's digest already sent.
    seed_session = sqlite_session_factory()
    seed_session.add(
        DailyDigest(
            digest_date=datetime.now(timezone.utc).date(),  # run_daily.main() now keys off UTC "today"
            summary_text="<p>already sent</p>",
            article_count=3,
            sent_at=datetime.now(timezone.utc),
        )
    )
    seed_session.commit()
    seed_session.close()

    monkeypatch.setattr(run_daily, "SessionLocal", sqlite_session_factory)
    monkeypatch.setattr(run_daily, "get_settings", lambda: Settings(digest_recipient_email="me@example.com"))

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("should not be called when digest already sent")

    monkeypatch.setattr(run_daily, "get_llm_provider", _fail_if_called)
    monkeypatch.setattr(run_daily, "get_email_sender", _fail_if_called)

    # Should return early without raising (the fakes above would raise if hit).
    run_daily.main(dry_run=False)
