import os
import smtplib
from email.message import EmailMessage
from langchain_core.tools import tool
import logging
from typing import Optional
import markdown

logger = logging.getLogger("email_tools")

@tool
def send_portfolio_email(
    subject: str,
    markdown_body: str,
    recipient_email: str
) -> str:
    """
    Send an email containing a portfolio analysis report.
    Use this tool ONLY when you have analyzed a portfolio and formulated market suggestions.
    
    Args:
        subject: The subject line of the email.
        markdown_body: The email body content formatted in Markdown.
        recipient_email: The email address to send the report to.
        
    Returns:
        Status message indicating success or failure.
    """
    logger.info("Attempting to send email to %s with subject '%s'", recipient_email, subject)
    
    # Read environment variables
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port_str = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not recipient_email or recipient_email.strip() == "":
        return "Failed: No recipient email provided. The user might be anonymous."
        
    if not smtp_user or not smtp_password:
        return (
            "Failed: SMTP credentials missing on server. Please ask the user to configure "
            "SMTP_USER and SMTP_PASSWORD environment variables."
        )
        
    try:
        smtp_port = int(smtp_port_str)
        
        # Convert markdown to HTML for a better looking email
        html_body = markdown.markdown(markdown_body)
        
        # Build the message
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient_email
        
        # Fallback text content (raw markdown)
        msg.set_content(markdown_body)
        
        # Add rich HTML alternative
        msg.add_alternative(html_body, subtype="html")
        
        # Connect and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            
        logger.info("Successfully sent email to %s", recipient_email)
        return "Email sent successfully!"
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return f"Failed: Could not send email due to a system error: {str(e)}"
