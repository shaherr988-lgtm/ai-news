"""Sanity-check the configured EMAIL_PROVIDER credentials in isolation,
before trusting the full pipeline. Run with: python -m scripts.test_email
"""

from apps.core.config import get_settings
from apps.pipeline.mailer import get_email_sender


def main() -> None:
    settings = get_settings()
    if not settings.digest_recipient_email:
        raise SystemExit("Set DIGEST_RECIPIENT_EMAIL in .env before running this script.")

    sender = get_email_sender(settings)
    sender.send(
        to=settings.digest_recipient_email,
        subject="ai news — رسالة اختبار",
        html_body="<p>لو وصلتك هذي الرسالة، إعدادات الإرسال شغّالة صح.</p>",
    )
    print(f"Test email sent to {settings.digest_recipient_email} via {settings.email_provider}.")


if __name__ == "__main__":
    main()
