"""
WhatsApp webhook API endpoint.
GET  /webhook — Meta verification handshake
POST /webhook — Incoming message processing
"""

import logging
from fastapi import APIRouter, Request, Response, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.db.models import Seller
from app.whatsapp.webhook_parser import parse_webhook_payload, verify_webhook_signature
from app.whatsapp.client import whatsapp_client
from app.services.customer_service import customer_service
from app.services.conversation_service import conversation_service
from app.services.notification_service import notification_service
from app.agent.engine import agent_engine
from sqlalchemy import select

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta webhook verification handshake."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WA_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning(f"Webhook verification failed: mode={mode}")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle incoming WhatsApp messages.
    Returns 200 immediately (Meta requirement), processes in background.
    """
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature")
        return Response(content="Invalid signature", status_code=403)

    data = await request.json()

    # Parse messages from payload
    messages = parse_webhook_payload(data)

    if not messages:
        return {"status": "ok"}  # Status update or other non-message event

    # Process each message in background
    for msg in messages:
        background_tasks.add_task(
            _process_message,
            wa_message_id=msg.wa_message_id,
            from_number=msg.from_number,
            text=msg.text,
            phone_number_id=msg.phone_number_id,
        )

    return {"status": "ok"}


async def _process_message(
    wa_message_id: str,
    from_number: str,
    text: str,
    phone_number_id: str,
):
    """
    Process a single incoming message through the agent pipeline.
    Runs as a background task so the webhook returns 200 immediately.
    """
    from app.db.database import async_session_factory

    async with async_session_factory() as db:
        try:
            # Find the seller by phone number ID
            stmt = select(Seller).where(
                Seller.wa_phone_number_id == phone_number_id
            )
            result = await db.execute(stmt)
            seller = result.scalar_one_or_none()

            if not seller:
                # Fallback: use the first seller (single-tenant)
                result = await db.execute(select(Seller).limit(1))
                seller = result.scalar_one_or_none()

            if not seller:
                logger.error("No seller found in database")
                return

            # Get or create customer
            customer, is_new = await customer_service.get_or_create(
                db, seller.id, from_number
            )

            # Get or create conversation
            convo, is_new_convo = await conversation_service.get_or_create_active(
                db, customer.id, seller.id
            )

            # Check for duplicate message
            if await conversation_service.is_message_duplicate(db, wa_message_id):
                logger.info(f"Duplicate message {wa_message_id}, skipping")
                await db.commit()
                return

            # Store the incoming message
            await conversation_service.add_message(
                db=db,
                conversation_id=convo.id,
                sender="customer",
                content=text,
                wa_message_id=wa_message_id,
            )

            # Notify dashboard
            await notification_service.push_new_message(
                seller.id, convo.id, "customer", text
            )

            # Run the agent
            agent_reply = await agent_engine.process_message(
                db=db,
                customer_id=customer.id,
                conversation_id=convo.id,
                seller=seller,
                incoming_message=text,
            )

            # Store the agent's reply
            await conversation_service.add_message(
                db=db,
                conversation_id=convo.id,
                sender="agent",
                content=agent_reply,
            )

            await db.commit()

            # Send reply via WhatsApp (after commit, so DB state is consistent)
            await whatsapp_client.send_text_message(
                to_number=from_number,
                message=agent_reply,
                phone_number_id=seller.wa_phone_number_id or settings.WA_PHONE_NUMBER_ID,
                access_token=seller.wa_access_token or settings.WA_ACCESS_TOKEN,
                last_customer_message_at=convo.last_customer_message_at,
            )

            # Notify dashboard of agent reply
            await notification_service.push_new_message(
                seller.id, convo.id, "agent", agent_reply
            )

        except Exception as e:
            logger.error(f"Error processing message from {from_number}: {e}", exc_info=True)
            await db.rollback()

            # Never silence — send a fallback message
            try:
                await whatsapp_client.send_text_message(
                    to_number=from_number,
                    message="I'm having a little trouble right now — let me check and get back to you shortly 🙏",
                )
            except Exception:
                pass
