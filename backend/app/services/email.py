import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("careerpilot.email")


def _send_brevo_api(s, to: str, subject: str, body: str) -> None:
    """Send through Brevo's HTTPS API (port 443). Free hosts that block SMTP ports still allow this."""
    import httpx
    from email.utils import parseaddr

    name, addr = parseaddr(s.EMAIL_FROM)
    if not s.BREVO_API_KEY or not addr:
        log.error("BREVO_API_KEY or EMAIL_FROM is not configured; email not sent")
        return
    try:
        r = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": s.BREVO_API_KEY, "accept": "application/json", "content-type": "application/json"},
            json={"sender": {"name": name or "CareerPilot AI", "email": addr}, "to": [{"email": to}],
                  "subject": subject, "textContent": body},
            timeout=15,
        )
        if r.status_code >= 300:
            # Log only the status and Brevo's short error code/message; never the key or the email body.
            detail = ""
            try:
                detail = str(r.json().get("message", ""))[:160]
            except Exception:
                pass
            log.error("Brevo API rejected the email: HTTP %s %s", r.status_code, detail)
    except Exception as e:
        log.error("Brevo API request failed: %s", type(e).__name__)


def send_email(to: str, subject: str, body: str, *, dev_link: str | None = None) -> None:
    """Send via SMTP, or print a clearly marked link in development console mode.

    `dev_link` is only ever printed when ENVIRONMENT is development/test AND EMAIL_MODE=console.
    In production it is never logged.
    """
    s = get_settings()
    if s.EMAIL_MODE == "console":
        if s.is_dev:
            print(f"\n===== LOCAL DEVELOPMENT EMAIL (not sent) =====\nTo: {to}\nSubject: {subject}\n{body}\n"
                  f"{'Link: ' + dev_link if dev_link else ''}\n===== END (development only) =====\n", flush=True)
        else:
            log.warning("EMAIL_MODE=console in production: email to a user was NOT sent. Configure SMTP.")
        return
    if s.EMAIL_MODE == "brevo_api":
        _send_brevo_api(s, to, subject, body)
        return
    if not s.SMTP_HOST:
        log.error("SMTP_HOST is not configured; email not sent")
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.EMAIL_FROM, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            if s.SMTP_USERNAME:
                smtp.login(s.SMTP_USERNAME, s.SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:  # never leak details or tokens
        log.error("Email delivery failed: %s", type(e).__name__)
