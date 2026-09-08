from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.core.config import get_settings
from apps.models import Base
from apps.models.digest import DailyDigest
from apps.web.main import app
from apps.web.routers import internal


def _client() -> TestClient:
    return TestClient(app)


def _sqlite_session_factory():
    # StaticPool + check_same_thread=False: the route runs on a different
    # thread than the test (FastAPI's threadpool for sync endpoints), and a
    # plain sqlite ":memory:" engine hands each thread its own empty database
    # otherwise, hiding the tables created below.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


def test_wrong_token_returns_404(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    response = _client().post("/internal/run-daily", params={"token": "wrong-token"})
    assert response.status_code == 404


def test_missing_configured_token_returns_404(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", None)
    response = _client().post("/internal/run-daily", params={"token": "anything"})
    assert response.status_code == 404


def test_correct_token_starts_the_pipeline_in_background(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    with patch("apps.web.routers.internal.run_daily_main") as mock_run:
        response = _client().post("/internal/run-daily", params={"token": "correct-token"})
        assert response.status_code == 200
        assert response.json() == {"status": "started"}
        mock_run.assert_called_once_with(dry_run=False)


def test_basic_auth_middleware_does_not_block_this_route(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "basic_auth_username", "user")
    monkeypatch.setattr(settings, "basic_auth_password", "pass")
    monkeypatch.setattr(settings, "run_daily_token", "correct-token")
    with patch("apps.web.routers.internal.run_daily_main"):
        # No Authorization header sent — would 401 on any other route.
        response = _client().post("/internal/run-daily", params={"token": "correct-token"})
        assert response.status_code == 200


def test_reset_today_digest_wrong_token_returns_404(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    response = _client().post("/internal/reset-today-digest", params={"token": "wrong-token"})
    assert response.status_code == 404


def test_reset_today_digest_clears_sent_at(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    session_factory = _sqlite_session_factory()
    seed = session_factory()
    seed.add(
        DailyDigest(
            digest_date=datetime.now(timezone.utc).date(),
            summary_text="<p>already sent</p>",
            article_count=1,
            sent_at=datetime.now(timezone.utc),
        )
    )
    seed.commit()
    seed.close()

    monkeypatch.setattr(internal, "SessionLocal", session_factory)

    response = _client().post("/internal/reset-today-digest", params={"token": "correct-token"})
    assert response.status_code == 200
    assert response.json() == {"status": "reset"}

    check = session_factory()
    digest = check.query(DailyDigest).filter_by(digest_date=datetime.now(timezone.utc).date()).first()
    assert digest.sent_at is None
    check.close()


def test_reset_today_digest_when_no_digest_exists(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    monkeypatch.setattr(internal, "SessionLocal", _sqlite_session_factory())

    response = _client().post("/internal/reset-today-digest", params={"token": "correct-token"})
    assert response.status_code == 200
    assert response.json() == {"status": "no digest found for today"}


def test_seed_sources_wrong_token_returns_404(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    response = _client().post("/internal/seed-sources", params={"token": "wrong-token"})
    assert response.status_code == 404


def test_seed_sources_calls_seed_and_returns_count(monkeypatch):
    monkeypatch.setattr(get_settings(), "run_daily_token", "correct-token")
    with patch("apps.web.routers.internal.seed_sources", return_value=8) as mock_seed:
        response = _client().post("/internal/seed-sources", params={"token": "correct-token"})
        assert response.status_code == 200
        assert response.json() == {"status": "seeded", "added": 8}
        mock_seed.assert_called_once_with()
