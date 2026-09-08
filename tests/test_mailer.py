from unittest.mock import patch

import pytest

from apps.core.config import Settings
from apps.pipeline.mailer import BrevoAPISender, GmailSMTPSender, OutlookSMTPSender, get_email_sender


def test_returns_gmail_sender_when_configured():
    settings = Settings(email_provider="gmail", gmail_address="me@gmail.com", gmail_app_password="x")
    sender = get_email_sender(settings)
    assert isinstance(sender, GmailSMTPSender)


def test_returns_outlook_sender_when_configured():
    settings = Settings(
        email_provider="outlook", outlook_address="me@outlook.com", outlook_app_password="x"
    )
    sender = get_email_sender(settings)
    assert isinstance(sender, OutlookSMTPSender)


def test_unknown_email_provider_raises():
    settings = Settings(email_provider="not-a-real-provider")
    with pytest.raises(ValueError):
        get_email_sender(settings)


def test_gmail_sender_requires_credentials():
    with pytest.raises(ValueError):
        GmailSMTPSender("", "")


def test_outlook_sender_requires_credentials():
    with pytest.raises(ValueError):
        OutlookSMTPSender("", "")


def test_returns_brevo_sender_when_configured():
    settings = Settings(
        email_provider="brevo",
        brevo_api_key="key",
        brevo_sender_email="me@example.com",
    )
    sender = get_email_sender(settings)
    assert isinstance(sender, BrevoAPISender)


def test_brevo_sender_requires_all_credentials():
    with pytest.raises(ValueError):
        BrevoAPISender("", "")
    with pytest.raises(ValueError):
        BrevoAPISender("key", "")


def test_brevo_sender_posts_to_api_with_split_recipients():
    sender = BrevoAPISender("api-key", "sender@example.com")
    fake_response = type("Response", (), {"status_code": 201, "text": "ok"})()
    with patch("apps.pipeline.mailer.requests.post", return_value=fake_response) as mock_post:
        sender.send(to="a@example.com, b@example.com", subject="Subject", html_body="<p>Hi</p>")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.brevo.com/v3/smtp/email"
    assert kwargs["headers"]["api-key"] == "api-key"
    assert kwargs["json"]["to"] == [{"email": "a@example.com"}, {"email": "b@example.com"}]
    assert kwargs["json"]["sender"] == {"email": "sender@example.com"}


def test_brevo_sender_raises_on_error_response():
    sender = BrevoAPISender("api-key", "sender@example.com")
    fake_response = type("Response", (), {"status_code": 401, "text": "unauthorized"})()
    with patch("apps.pipeline.mailer.requests.post", return_value=fake_response):
        with pytest.raises(RuntimeError):
            sender.send(to="a@example.com", subject="Subject", html_body="<p>Hi</p>")
