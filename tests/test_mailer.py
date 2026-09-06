import pytest

from apps.core.config import Settings
from apps.pipeline.mailer import BrevoSMTPSender, GmailSMTPSender, OutlookSMTPSender, get_email_sender


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
        brevo_smtp_login="login",
        brevo_smtp_key="key",
        brevo_sender_email="me@example.com",
    )
    sender = get_email_sender(settings)
    assert isinstance(sender, BrevoSMTPSender)


def test_brevo_sender_requires_all_credentials():
    with pytest.raises(ValueError):
        BrevoSMTPSender("", "", "")
    with pytest.raises(ValueError):
        BrevoSMTPSender("login", "key", "")
