"""
Baileys Service
Handles parsing incoming WhatsApp messages from the Baileys Node.js service
and sending replies back through it.
"""

import logging
import httpx

from backend.config import get_settings
from backend.models import IncomingMessage

logger = logging.getLogger(__name__)


def parse_incoming_message(json_data: dict) -> IncomingMessage:
    """
    Parse the incoming message from the Baileys Node.js service.

    Baileys forwards JSON with fields:
    - phone: "+919999999999"
    - message: "Hello"
    - profile_name: "User's WhatsApp display name"

    Args:
        json_data: Dict from Baileys HTTP POST

    Returns:
        IncomingMessage with phone, message text, and profile name
    """
    phone = json_data.get("phone", "").strip()
    message = json_data.get("message", "").strip()
    profile_name = json_data.get("profile_name", "")

    logger.info(f"Incoming Baileys message from {phone}: {message[:50]}...")

    return IncomingMessage(
        phone=phone,
        message=message,
        profile_name=profile_name or None,
    )


async def send_whatsapp_reply(to_phone: str, body: str):
    """
    Send a WhatsApp reply via the Baileys Node.js service.

    Makes an HTTP POST to the Baileys service's /send endpoint,
    which then sends the message through WhatsApp Web.

    Args:
        to_phone: Recipient phone number (e.g., +919999999999)
        body: Message text to send
    """
    settings = get_settings()
    url = f"{settings.baileys_service_url}/send"

    payload = {
        "phone": to_phone,
        "message": body,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            logger.info(f"WhatsApp reply sent to {to_phone} via Baileys")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Baileys service error: {e.response.status_code} — {e.response.text}"
        )
        raise
    except httpx.ConnectError:
        logger.error(
            "Cannot connect to Baileys service. "
            f"Is it running at {settings.baileys_service_url}?"
        )
        raise
    except Exception as e:
        logger.error(f"Failed to send WhatsApp reply via Baileys: {e}")
        raise
