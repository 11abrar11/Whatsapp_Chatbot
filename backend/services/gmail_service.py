"""
Gmail Service
Sends escalation emails via SMTP when financial queries are detected.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from backend.config import get_settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


async def send_escalation_email(
    phone: str,
    user_message: str,
    lead_score: int,
    lead_status: str,
    summary: str,
):
    """
    Send an escalation email to the team via Gmail SMTP.
    
    Called when the chatbot detects a financial query (pricing, discounts,
    quotations, refunds, invoices, payments, contracts, legal).
    
    Args:
        phone: Customer's phone number
        user_message: The message that triggered escalation
        lead_score: Current lead score (0-100)
        lead_status: Current lead status
        summary: Lead conversation summary
    """
    settings = get_settings()

    if not settings.gmail_sender or not settings.gmail_app_password:
        logger.error("Gmail credentials not configured — skipping escalation email")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Financial Query Escalation"
    msg["From"] = settings.gmail_sender
    msg["To"] = settings.escalation_recipient

    # Plain text body
    text_body = f"""Financial Query Escalation
{'=' * 40}

Phone Number: {phone}

Latest User Message:
{user_message}

Lead Score: {lead_score}/100

Lead Status: {lead_status}

Summary:
{summary}

Timestamp: {timestamp}

---
This is an automated escalation from the PP5 WhatsApp Chatbot.
Please follow up with this lead at your earliest convenience.
"""

    # HTML body for better formatting
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #1a1a2e; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="margin: 0;">⚠️ Financial Query Escalation</h2>
    </div>
    <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 8px 8px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Phone Number</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{phone}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Lead Score</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{lead_score}/100</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #eee;">Lead Status</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{lead_status}</td>
            </tr>
        </table>
        
        <h3 style="margin-top: 20px;">Latest User Message</h3>
        <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; border-left: 4px solid #e74c3c;">
            {user_message}
        </div>
        
        <h3>Lead Summary</h3>
        <div style="background-color: #f5f5f5; padding: 12px; border-radius: 6px; border-left: 4px solid #3498db;">
            {summary}
        </div>
        
        <p style="color: #888; font-size: 12px; margin-top: 20px;">
            Timestamp: {timestamp}<br>
            Automated escalation from PP5 WhatsApp Chatbot
        </p>
    </div>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(settings.gmail_sender, settings.gmail_app_password)
            server.send_message(msg)

        logger.info(
            f"Escalation email sent to {settings.escalation_recipient} "
            f"for lead {phone}"
        )
    except Exception as e:
        logger.error(f"Failed to send escalation email: {e}")
        # Don't raise — escalation failure shouldn't block the WhatsApp reply
