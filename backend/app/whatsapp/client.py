"""
WhatsApp Business Cloud API client.
Handles sending messages with 24-hour session window awareness (Gap #4).
"""

import logging
from datetime import datetime, timezone, timedelta
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SESSION_WINDOW_HOURS = 24
WARNING_THRESHOLD_HOURS = 20  # Alert seller at 20h


class WhatsAppClient:
    """Send messages via WhatsApp Business Cloud API."""

    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{settings.WA_API_VERSION}"
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def send_text_message(
        self,
        to_number: str,
        message: str,
        phone_number_id: str | None = None,
        access_token: str | None = None,
        last_customer_message_at: datetime | None = None,
    ) -> dict:
        """
        Send a text message. Checks 24-hour window (Gap #4).
        Falls back to template message if outside window.
        """
        phone_id = phone_number_id or settings.WA_PHONE_NUMBER_ID
        token = access_token or settings.WA_ACCESS_TOKEN

        if not phone_id or not token:
            logger.error("WhatsApp credentials not configured")
            return {"status": "error", "message": "WhatsApp credentials not configured"}

        # Gap #4: Check 24-hour session window
        if last_customer_message_at:
            now = datetime.now(timezone.utc)
            window_end = last_customer_message_at + timedelta(hours=SESSION_WINDOW_HOURS)

            if now > window_end:
                logger.info(f"Outside 24h window for {to_number}, using template message")
                return await self.send_template_message(
                    to_number=to_number,
                    template_name="follow_up",
                    parameters=[message[:100]],
                    phone_number_id=phone_id,
                    access_token=token,
                )

        # Inside window — send normal text
        url = f"{self.base_url}/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Message sent to {to_number}")
            return {"status": "sent", "wa_message_id": data.get("messages", [{}])[0].get("id")}
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error: {e.response.status_code} - {e.response.text}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        parameters: list[str] | None = None,
        phone_number_id: str | None = None,
        access_token: str | None = None,
        language_code: str = "en_US",
    ) -> dict:
        """
        Gap #4: Send a pre-approved template message (for outside 24h window).
        Templates must be pre-approved in Meta Business Manager.
        """
        phone_id = phone_number_id or settings.WA_PHONE_NUMBER_ID
        token = access_token or settings.WA_ACCESS_TOKEN

        url = f"{self.base_url}/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        template = {
            "name": template_name,
            "language": {"code": language_code},
        }

        if parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": p} for p in parameters
                    ],
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": template,
        }

        try:
            response = await self.http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Template '{template_name}' sent to {to_number}")
            return {"status": "sent", "wa_message_id": data.get("messages", [{}])[0].get("id")}
        except Exception as e:
            logger.error(f"Template send failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def is_session_expiring_soon(self, last_customer_message_at: datetime) -> bool:
        """Gap #4: Check if the session window is about to expire (for dashboard warnings)."""
        if not last_customer_message_at:
            return False
        now = datetime.now(timezone.utc)
        hours_elapsed = (now - last_customer_message_at).total_seconds() / 3600
        return hours_elapsed >= WARNING_THRESHOLD_HOURS

    async def close(self):
        await self.http_client.aclose()


# Singleton
whatsapp_client = WhatsAppClient()
