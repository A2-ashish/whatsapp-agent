"""
Context Builder — assembles the focused context window for each agent invocation.
Balances completeness vs. cost/latency.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Customer, Order, Escalation, Conversation
from app.services.conversation_service import conversation_service
from dataclasses import dataclass


@dataclass
class ConversationContext:
    recent_messages: list
    customer_summary: str
    active_escalation: dict | None
    is_paused: bool


class ContextBuilder:

    async def build(
        self,
        db: AsyncSession,
        conversation_id: str,
        customer_id: str,
        max_messages: int = 20,
    ) -> ConversationContext:
        # 1. Recent messages
        recent_messages = await conversation_service.get_recent_messages(
            db, conversation_id, limit=max_messages
        )

        # 2. Customer summary
        customer_summary = await self._build_customer_summary(db, customer_id)

        # 3. Active escalation check
        convo = await db.get(Conversation, conversation_id)
        active_escalation = None
        is_paused = False

        if convo and convo.is_paused and convo.paused_escalation_id:
            is_paused = True
            escalation = await db.get(Escalation, convo.paused_escalation_id)
            if escalation:
                active_escalation = {
                    "escalation_id": escalation.id,
                    "reason": escalation.reason,
                    "status": escalation.status,
                    "conversation_summary": escalation.conversation_summary,
                }

        return ConversationContext(
            recent_messages=recent_messages,
            customer_summary=customer_summary,
            active_escalation=active_escalation,
            is_paused=is_paused,
        )

    async def _build_customer_summary(self, db: AsyncSession, customer_id: str) -> str:
        """Build a concise customer summary for the system prompt."""
        customer = await db.get(Customer, customer_id)
        if not customer:
            return "New customer, no history available."

        # Count past orders and total spent
        stmt = select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total), 0),
        ).where(Order.customer_id == customer_id)
        result = await db.execute(stmt)
        row = result.one()
        order_count = row[0]
        total_spent = row[1]

        parts = []
        if order_count > 0:
            avg = total_spent / order_count
            parts.append(
                f"Returning customer. {order_count} past orders, total spent ₹{total_spent:.0f}, avg ₹{avg:.0f}."
            )
        else:
            parts.append("New customer, first interaction.")

        if customer.name:
            parts.insert(0, f"Name: {customer.name}.")

        if customer.notes:
            parts.append(f"Owner's notes: \"{customer.notes}\"")

        return " ".join(parts)


context_builder = ContextBuilder()
