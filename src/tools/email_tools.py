# [ignoring loop detection]
import os
import logging
from typing import Optional
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool

try:
    import markdown as _md_lib  # type: ignore
    _MD_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MD_AVAILABLE = False

logger = logging.getLogger("email_tools")

SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"


def _send_via_smtp(
    subject: str,
    markdown_body: str,
    html_body: str,
    recipient_email: str,
    from_email: str,
) -> str:
    """
    Send email via SMTP (Gmail, etc.).
    Used as fallback when SendGrid is not configured.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_user, smtp_password]):
        return "Failed: SMTP configuration incomplete (SMTP_SERVER, SMTP_USER, SMTP_PASSWORD required)."

    try:
        # Create MIME message with both plain text and HTML parts
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = recipient_email

        part1 = MIMEText(markdown_body, "plain")
        part2 = MIMEText(html_body, "html")

        msg.attach(part1)
        msg.attach(part2)

        # Connect and send (type assertions safe due to all() check above)
        smtp_port_int = int(smtp_port)
        with smtplib.SMTP(smtp_server or "", smtp_port_int, timeout=10) as server:  # type: ignore
            server.starttls()
            server.login(smtp_user or "", smtp_password or "")  # type: ignore
            server.send_message(msg)

        logger.info("Successfully sent email to %s via SMTP", recipient_email)
        return "Email sent successfully!"
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to send email via SMTP: %s", exc)
        return f"Failed: Could not send email due to SMTP error: {exc}"


def _send_via_sendgrid(
    subject: str,
    markdown_body: str,
    html_body: str,
    recipient_email: str,
    from_email: str,
) -> Optional[str]:
    """
    Send email via SendGrid API.
    Returns error string if successful/failed, None if not configured (to fall back to SMTP).
    """
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    if not sendgrid_key:
        return None  # Signal to fall back to SMTP

    # SendGrid expects both plain‑text and HTML parts.
    payload = {
        "personalizations": [{"to": [{"email": recipient_email}], "subject": subject}],
        "from": {"email": from_email},
        "content": [
            {"type": "text/plain", "value": markdown_body},
            {"type": "text/html", "value": html_body},
        ],
    }

    headers = {
        "Authorization": f"Bearer {sendgrid_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(SENDGRID_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("Successfully sent email to %s via SendGrid", recipient_email)
        return "Email sent successfully!"
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to send email via SendGrid: %s", exc)
        return f"Failed: Could not send email via SendGrid: {exc}"


@tool
def send_portfolio_email(
    subject: str,
    markdown_body: str,
    recipient_email: str,
) -> str:
    """
    Send an email containing a portfolio analysis report.
    Tries SendGrid first (if configured), then falls back to SMTP.
    Returns a status message.
    """
    if not recipient_email or recipient_email.strip() == "":
        return "Failed: No recipient email provided."

    # Use the configured FROM address if provided, otherwise a generic placeholder.
    from_email = os.getenv("SMTP_USER", "no-reply@example.com")

    # Convert markdown body to HTML for the rich-text part of the email.
    if _MD_AVAILABLE:
        html_body = _md_lib.markdown(  # type: ignore
            markdown_body,
            extensions=["tables", "fenced_code", "nl2br"],
        )
    else:  # pragma: no cover
        # Basic fallback: wrap in <pre> so whitespace is preserved.
        html_body = f"<pre>{markdown_body}</pre>"

    # Try SendGrid first if configured
    sendgrid_result = _send_via_sendgrid(subject, markdown_body, html_body, recipient_email, from_email)
    if sendgrid_result is not None:
        return sendgrid_result

    # Fall back to SMTP (local/Gmail)
    return _send_via_smtp(subject, markdown_body, html_body, recipient_email, from_email)
