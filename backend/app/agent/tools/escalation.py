"""
Tool: escalate_to_owner
Creates escalation, pauses conversation, notifies seller via SSE.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Escalation
from app.services.conversation_service import conversation_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)


async def escalate_to_owner(
    db: AsyncSession,
    seller_id: str,
    customer_id: str,
    conversation_id: str,
    reason: str,
    conversation_summary: str,
    suggested_action: str,
) -> dict:
    """
    Hand off to the business owner:
    1. Create escalation record
    2. Pause the conversation (Gap #3)
    3. Push SSE notification to dashboard
    """
    escalation = Escalation(
        seller_id=seller_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        reason=reason,
        conversation_summary=conversation_summary,
        suggested_action=suggested_action,
        status="open",
    )
    db.add(escalation)
    await db.flush()

    # Gap #3: Pause the conversation
    await conversation_service.pause_for_escalation(
        db, conversation_id, escalation.id
    )

    # Push real-time notification
    await notification_service.push_new_escalation(seller_id, {
        "escalation_id": escalation.id,
        "customer_id": customer_id,
        "conversation_id": conversation_id,
        "reason": reason,
        "conversation_summary": conversation_summary,
        "suggested_action": suggested_action,
    })

    logger.info(f"Escalation {escalation.id} created: {reason}")

    return {
        "status": "escalated",
        "escalation_id": escalation.id,
        "message": "Escalation created. The conversation is paused. Tell the customer you're checking with the owner and will get back to them.",
    }
