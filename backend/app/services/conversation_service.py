"""
Conversation service — lifecycle management, advisory locking (Gap #5),
pause/unpause for escalations (Gap #3).
"""

from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Conversation, Message


class ConversationService:

    async def get_or_create_active(
        self, db: AsyncSession, customer_id: str, seller_id: str
    ) -> tuple[Conversation, bool]:
        """Get active conversation or create a new one."""
        stmt = select(Conversation).where(
            Conversation.customer_id == customer_id,
            Conversation.seller_id == seller_id,
            Conversation.status == "active",
        )
        result = await db.execute(stmt)
        convo = result.scalar_one_or_none()

        if convo:
            return convo, False

        convo = Conversation(
            customer_id=customer_id,
            seller_id=seller_id,
        )
        db.add(convo)
        await db.flush()
        return convo, True

    async def acquire_lock(self, db: AsyncSession, conversation_id: str):
        """
        Gap #5: Per-conversation advisory lock.
        Uses PostgreSQL pg_advisory_xact_lock with a hash of the conversation ID.
        Lock is released when the transaction commits/rollbacks.
        """
        lock_id = hash(conversation_id) % (2**31)
        await db.execute(text(f"SELECT pg_advisory_xact_lock({lock_id})"))

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        sender: str,
        content: str,
        tool_calls_json: dict | list | None = None,
        wa_message_id: str | None = None,
    ) -> Message:
        """Add a message to a conversation and update timestamps."""
        msg = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            tool_calls_json=tool_calls_json,
            wa_message_id=wa_message_id,
        )
        db.add(msg)

        # Update conversation timestamps
        convo = await db.get(Conversation, conversation_id)
        if convo:
            convo.last_message_at = datetime.now(timezone.utc)
            if sender == "customer":
                convo.last_customer_message_at = datetime.now(timezone.utc)

        await db.flush()
        return msg

    async def get_recent_messages(
        self, db: AsyncSession, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        """Get the most recent N messages for context building."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological order
        return messages

    async def pause_for_escalation(
        self, db: AsyncSession, conversation_id: str, escalation_id: str
    ):
        """Gap #3: Pause conversation when escalation is created."""
        convo = await db.get(Conversation, conversation_id)
        if convo:
            convo.is_paused = True
            convo.paused_escalation_id = escalation_id
            await db.flush()

    async def unpause(self, db: AsyncSession, conversation_id: str):
        """Gap #3: Unpause conversation when escalation is resolved."""
        convo = await db.get(Conversation, conversation_id)
        if convo:
            convo.is_paused = False
            convo.paused_escalation_id = None
            await db.flush()

    async def is_message_duplicate(self, db: AsyncSession, wa_message_id: str) -> bool:
        """Check if a WhatsApp message ID has already been processed."""
        if not wa_message_id:
            return False
        stmt = select(Message).where(Message.wa_message_id == wa_message_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def close_conversation(self, db: AsyncSession, conversation_id: str):
        convo = await db.get(Conversation, conversation_id)
        if convo:
            convo.status = "closed"
            await db.flush()

    async def get_by_id(self, db: AsyncSession, conversation_id: str) -> Conversation | None:
        return await db.get(Conversation, conversation_id)


conversation_service = ConversationService()
