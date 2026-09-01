"""
WhatsApp webhook parser — extracts message data from Meta webhook payloads
and verifies request signatures.
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ParsedMessage:
    wa_message_id: str
    from_number: str
    text: str
    timestamp: str
    message_type: str  # text, image, location, etc.
    phone_number_id: str  # Which business number received it


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the X-Hub-Signature-256 header against the app secret.
    Prevents webhook spoofing.
    """
    if not settings.WA_APP_SECRET:
        logger.warning("WA_APP_SECRET not configured — skipping signature verification")
        return True

    expected = hmac.new(
        settings.WA_APP_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


def parse_webhook_payload(data: dict) -> list[ParsedMessage]:
    """
    Parse a WhatsApp Cloud API webhook payload.
    Returns a list of parsed messages (usually 1, but can be batched).
    """
    messages = []

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id", "")

                for msg in value.get("messages", []):
                    msg_type = msg.get("type", "unknown")
                    text = ""

                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "")
                    elif msg_type == "image":
                        text = "[Customer sent an image]"
                        caption = msg.get("image", {}).get("caption", "")
                        if caption:
                            text += f" Caption: {caption}"
                    elif msg_type == "location":
                        loc = msg.get("location", {})
                        text = f"[Customer shared location: {loc.get('latitude')}, {loc.get('longitude')}]"
                    elif msg_type == "document":
                        text = "[Customer sent a document]"
                    elif msg_type == "audio":
                        text = "[Customer sent a voice message]"
                    elif msg_type == "video":
                        text = "[Customer sent a video]"
                    elif msg_type == "sticker":
                        text = "[Customer sent a sticker]"
                    elif msg_type == "reaction":
                        continue  # Skip reactions
                    else:
                        text = f"[Customer sent a {msg_type} message]"

                    if text:
                        messages.append(ParsedMessage(
                            wa_message_id=msg.get("id", ""),
                            from_number=msg.get("from", ""),
                            text=text,
                            timestamp=msg.get("timestamp", ""),
                            message_type=msg_type,
                            phone_number_id=phone_number_id,
                        ))

    except Exception as e:
        logger.error(f"Error parsing webhook payload: {e}", exc_info=True)

    return messages
