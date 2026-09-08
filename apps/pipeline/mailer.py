"""Email-sending abstraction. Gmail or Outlook SMTP, or Brevo over its HTTPS
API; swap in another provider later by adding an EmailSender subclass and a
branch in get_email_sender()."""

import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage

import requests

from apps.core.config import Settings, get_settings


class EmailSender(ABC):
    @abstractmethod
    def send(self, *, to: str, subject: str, html_body: str) -> None:
        raise NotImplementedError


def _build_message(*, address: str, to: str, subject: str, html_body: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = address
    message["To"] = to
    message.set_content("This email requires an HTML-capable client to view.")
    message.add_alternative(html_body, subtype="html")
    return message


def _send_via_starttls(*, host: str, port: int, login: str, password: str, message: EmailMessage) -> None:
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(login, password)
        smtp.send_message(message)


class GmailSMTPSender(EmailSender):
    def __init__(self, address: str, app_password: str):
        if not address or not app_password:
            raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD are required to send email")
        self._address = address
        self._app_password = app_password

    def send(self, *, to: str, subject: str, html_body: str) -> None:
        message = _build_message(address=self._address, to=to, subject=subject, html_body=html_body)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(self._address, self._app_password)
            smtp.send_message(message)


class OutlookSMTPSender(EmailSender):
    """Microsoft 365 organizational accounts with SMTP AUTH enabled by an
    admin. Does NOT work for personal Outlook.com/Hotmail accounts — Microsoft
    disables SMTP AUTH server-side for those with no user-facing way to
    re-enable it (confirmed via Microsoft's own support docs). Use "brevo"
    instead for a personal-account sender."""

    def __init__(self, address: str, app_password: str):
        if not address or not app_password:
            raise ValueError("OUTLOOK_ADDRESS and OUTLOOK_APP_PASSWORD are required to send email")
        self._address = address
        self._app_password = app_password

    def send(self, *, to: str, subject: str, html_body: str) -> None:
        message = _build_message(address=self._address, to=to, subject=subject, html_body=html_body)
        _send_via_starttls(
            host="smtp-mail.outlook.com", port=587, login=self._address, password=self._app_password,
            message=message,
        )


class BrevoAPISender(EmailSender):
    """Brevo (formerly Sendinblue) — a dedicated transactional email service,
    free tier 300 emails/day. Sends over Brevo's HTTPS API rather than SMTP:
    Render (like most PaaS free tiers) blocks outbound SMTP ports (25/465/587)
    entirely, so smtp-relay.brevo.com:587 connections there just hang and
    time out (`TimeoutError: [Errno 110] Connection timed out`) even though
    the exact same code works from a home/office network. HTTPS on port 443
    isn't blocked. The API key comes from the Brevo dashboard (Settings ->
    SMTP & API -> API keys & MCP), not the SMTP key/login pair used before.
    `sender_email` must be a verified sender in Brevo (Senders, Domains &
    Dedicated IPs)."""

    _ENDPOINT = "https://api.brevo.com/v3/smtp/email"

    def __init__(self, api_key: str, sender_email: str):
        if not api_key or not sender_email:
            raise ValueError("BREVO_API_KEY and BREVO_SENDER_EMAIL are both required")
        self._api_key = api_key
        self._sender_email = sender_email

    def send(self, *, to: str, subject: str, html_body: str) -> None:
        recipients = [{"email": address.strip()} for address in to.split(",") if address.strip()]
        response = requests.post(
            self._ENDPOINT,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": self._api_key,
            },
            json={
                "sender": {"email": self._sender_email},
                "to": recipients,
                "subject": subject,
                "htmlContent": html_body,
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Brevo API send failed ({response.status_code}): {response.text}")


def get_email_sender(settings: Settings | None = None) -> EmailSender:
    settings = settings or get_settings()
    provider = settings.email_provider.lower().strip()

    if provider == "gmail":
        return GmailSMTPSender(settings.gmail_address or "", settings.gmail_app_password or "")

    if provider == "outlook":
        return OutlookSMTPSender(settings.outlook_address or "", settings.outlook_app_password or "")

    if provider == "brevo":
        return BrevoAPISender(settings.brevo_api_key or "", settings.brevo_sender_email or "")

    raise ValueError(
        f"Unknown EMAIL_PROVIDER: {settings.email_provider!r} (expected 'gmail', 'outlook', or 'brevo')"
    )
