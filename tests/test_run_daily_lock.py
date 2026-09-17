"""Verifies the Postgres advisory lock in apps/pipeline/run_daily.py: two
overlapping run_daily() calls must not both execute the pipeline — see
_DAILY_RUN_LOCK_KEY's docstring for why (two of the 4 redundant daily
triggers firing minutes apart, before either commits a sent digest, doubled
real LLM API usage and burned through Gemini's shared 20/day quota on
2026-09-17)."""

from unittest.mock import MagicMock, patch

from apps.pipeline import run_daily


def _fake_postgres_db(lock_acquired: bool) -> MagicMock:
    db = MagicMock()
    db.bind.dialect.name = "postgresql"
    db.execute.return_value.scalar.return_value = lock_acquired
    return db


def test_runs_the_pipeline_when_lock_is_acquired(monkeypatch):
    db = _fake_postgres_db(lock_acquired=True)
    monkeypatch.setattr(run_daily, "SessionLocal", lambda: db)

    with patch("apps.pipeline.run_daily._run") as mock_run:
        run_daily.main(dry_run=False)

    mock_run.assert_called_once_with(db, run_daily.get_settings(), False)
    db.close.assert_called_once()


def test_skips_the_pipeline_when_another_run_holds_the_lock(monkeypatch):
    db = _fake_postgres_db(lock_acquired=False)
    monkeypatch.setattr(run_daily, "SessionLocal", lambda: db)

    with patch("apps.pipeline.run_daily._run") as mock_run:
        run_daily.main(dry_run=False)

    mock_run.assert_not_called()
    db.close.assert_called_once()


def test_releases_the_lock_even_if_the_pipeline_raises(monkeypatch):
    db = _fake_postgres_db(lock_acquired=True)
    monkeypatch.setattr(run_daily, "SessionLocal", lambda: db)

    with patch("apps.pipeline.run_daily._run", side_effect=RuntimeError("boom")):
        try:
            run_daily.main(dry_run=False)
            assert False, "expected the exception to propagate"
        except RuntimeError:
            pass

    # Second db.execute call is the pg_advisory_unlock — must still happen.
    assert db.execute.call_count == 2
    db.close.assert_called_once()
