from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.core.config import get_settings
from apps.web.main import app


def _client() -> TestClient:
    return TestClient(app)


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
