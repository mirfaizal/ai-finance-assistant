# [ignoring loop detection]
import os
import logging
from typing import Optional
import requests
from langchain_core.tools import tool

try:
    import markdown as _md_lib  # type: ignore
    _MD_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MD_AVAILABLE = False

logger = logging.getLogger("email_tools")

SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"


@tool
def send_portfolio_email(
    subject: str,
    markdown_body: str,
    recipient_email: str,
) -> str:
    """
    Send an email containing a portfolio analysis report via SendGrid.
    Returns a status message.
    """
    if not recipient_email or recipient_email.strip() == "":
        return "Failed: No recipient email provided."

    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    if not sendgrid_key:
        return "Failed: SENDGRID_API_KEY not configured."

    # Use the configured FROM address if provided, otherwise a generic placeholder.
    from_email = os.getenv("SMTP_USER", "no-reply@example.com")

    # Convert markdown body to HTML for the rich-text part of the email.
    if _MD_AVAILABLE:
        html_body = _md_lib.markdown(
            markdown_body,
            extensions=["tables", "fenced_code", "nl2br"],
        )
    else:  # pragma: no cover
        # Basic fallback: wrap in <pre> so whitespace is preserved.
        html_body = f"<pre>{markdown_body}</pre>"

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
        return f"Failed: Could not send email due to a system error: {exc}"
