"""
Dashboard Conversations API — list + transcript viewer with tool call details.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Seller, Conversation, Customer, Message
from app.api.dashboard.auth import get_current_seller_dep

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/")
async def list_conversations(
    status: str | None = None,
    search: str | None = None,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Conversation, Customer)
        .join(Customer, Conversation.customer_id == Customer.id)
        .where(Conversation.seller_id == seller.id)
    )

    if status:
        stmt = stmt.where(Conversation.status == status)

    if search:
        stmt = stmt.where(
            Customer.whatsapp_number.ilike(f"%{search}%")
            | Customer.name.ilike(f"%{search}%")
        )

    stmt = stmt.order_by(Conversation.last_message_at.desc()).limit(50)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": convo.id,
            "customer_id": convo.customer_id,
            "customer_name": cust.name,
            "customer_phone": cust.whatsapp_number,
            "status": convo.status,
            "is_paused": convo.is_paused,
            "started_at": convo.started_at.isoformat() if convo.started_at else None,
            "last_message_at": convo.last_message_at.isoformat() if convo.last_message_at else None,
        }
        for convo, cust in rows
    ]


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    convo = await db.get(Conversation, conversation_id)
    if not convo or convo.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    customer = await db.get(Customer, convo.customer_id)

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return {
        "conversation": {
            "id": convo.id,
            "status": convo.status,
            "is_paused": convo.is_paused,
            "started_at": convo.started_at.isoformat() if convo.started_at else None,
        },
        "customer": {
            "id": customer.id if customer else None,
            "name": customer.name if customer else None,
            "whatsapp_number": customer.whatsapp_number if customer else None,
            "notes": customer.notes if customer else None,
        },
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "tool_calls": m.tool_calls_json,
            }
            for m in messages
        ],
    }
