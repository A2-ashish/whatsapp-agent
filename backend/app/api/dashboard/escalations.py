"""
Dashboard Escalations API — list, resolve (Gap #3: two resolution modes).
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, async_session_factory
from app.db.models import Seller, Escalation, Customer, Conversation
from app.schemas import EscalationResolve, EscalationResponse
from app.api.dashboard.auth import get_current_seller_dep
from app.services.conversation_service import conversation_service
from app.services.notification_service import notification_service
from app.whatsapp.client import whatsapp_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/escalations", tags=["escalations"])


@router.get("/", response_model=list[EscalationResponse])
async def list_escalations(
    status: str | None = "open",
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Escalation.seller_id == seller.id]
    if status:
        conditions.append(Escalation.status == status)

    stmt = (
        select(Escalation)
        .where(*conditions)
        .order_by(Escalation.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{escalation_id}")
async def get_escalation_detail(
    escalation_id: str,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    escalation = await db.get(Escalation, escalation_id)
    if not escalation or escalation.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Escalation not found")

    customer = await db.get(Customer, escalation.customer_id)

    # Get the conversation with session window info
    convo = await db.get(Conversation, escalation.conversation_id)
    session_expiring = False
    if convo and convo.last_customer_message_at:
        session_expiring = whatsapp_client.is_session_expiring_soon(
            convo.last_customer_message_at
        )

    return {
        "escalation": {
            "id": escalation.id,
            "reason": escalation.reason,
            "conversation_summary": escalation.conversation_summary,
            "suggested_action": escalation.suggested_action,
            "status": escalation.status,
            "created_at": escalation.created_at.isoformat() if escalation.created_at else None,
            "resolved_at": escalation.resolved_at.isoformat() if escalation.resolved_at else None,
            "resolution_notes": escalation.resolution_notes,
            "resolution_mode": escalation.resolution_mode,
        },
        "customer": {
            "id": customer.id if customer else None,
            "name": customer.name if customer else None,
            "whatsapp_number": customer.whatsapp_number if customer else None,
        },
        "session_window_expiring": session_expiring,
    }


@router.post("/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    resolve: EscalationResolve,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    Gap #3: Resolve an escalation with two modes:
    - instruct_agent: Give the agent an instruction, it resumes autonomously
    - direct_reply: Send a message directly to the customer
    """
    escalation = await db.get(Escalation, escalation_id)
    if not escalation or escalation.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if escalation.status == "resolved":
        raise HTTPException(status_code=400, detail="Escalation already resolved")

    customer = await db.get(Customer, escalation.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if resolve.mode == "direct_reply":
        # Send seller's message directly to customer via WhatsApp
        convo = await db.get(Conversation, escalation.conversation_id)

        await whatsapp_client.send_text_message(
            to_number=customer.whatsapp_number,
            message=resolve.content,
            phone_number_id=seller.wa_phone_number_id,
            access_token=seller.wa_access_token,
            last_customer_message_at=convo.last_customer_message_at if convo else None,
        )

        # Log as owner message
        await conversation_service.add_message(
            db=db,
            conversation_id=escalation.conversation_id,
            sender="owner",
            content=resolve.content,
        )

        # Unpause conversation
        await conversation_service.unpause(db, escalation.conversation_id)

        # Mark resolved
        escalation.status = "resolved"
        escalation.resolved_at = datetime.now(timezone.utc)
        escalation.resolution_notes = resolve.content
        escalation.resolution_mode = "direct_reply"
        await db.flush()

    elif resolve.mode == "instruct_agent":
        # Give the agent an instruction and let it resume
        from app.agent.engine import agent_engine

        # Mark resolved first
        escalation.status = "resolved"
        escalation.resolved_at = datetime.now(timezone.utc)
        escalation.resolution_notes = f"Seller instruction: {resolve.content}"
        escalation.resolution_mode = "instruct_agent"
        await db.flush()

        # Unpause conversation
        await conversation_service.unpause(db, escalation.conversation_id)

        # Run the agent with seller's instruction
        agent_reply = await agent_engine.resume_from_escalation(
            db=db,
            conversation_id=escalation.conversation_id,
            seller=seller,
            customer_id=escalation.customer_id,
            seller_instruction=resolve.content,
        )

        # Store and send agent's reply
        await conversation_service.add_message(
            db=db,
            conversation_id=escalation.conversation_id,
            sender="agent",
            content=agent_reply,
        )

        convo = await db.get(Conversation, escalation.conversation_id)
        await whatsapp_client.send_text_message(
            to_number=customer.whatsapp_number,
            message=agent_reply,
            phone_number_id=seller.wa_phone_number_id,
            access_token=seller.wa_access_token,
            last_customer_message_at=convo.last_customer_message_at if convo else None,
        )

    else:
        raise HTTPException(status_code=400, detail="Mode must be 'instruct_agent' or 'direct_reply'")

    # Push SSE update
    await notification_service.push(seller.id, "escalation_resolved", {
        "escalation_id": escalation.id,
        "mode": resolve.mode,
    })

    return {"status": "resolved", "escalation_id": escalation.id, "mode": resolve.mode}
