"""
Tool: log_action
Writes to agent_action_log for audit trail.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AgentActionLog


async def log_action(
    db: AsyncSession,
    seller_id: str,
    conversation_id: str,
    action: str,
    details: dict | None = None,
    tokens_used: int | None = None,
    estimated_cost_inr: float | None = None,
) -> dict:
    """Log an agent action to the audit trail."""
    log_entry = AgentActionLog(
        seller_id=seller_id,
        conversation_id=conversation_id,
        action_type=action,
        details_json=details,
        tokens_used=tokens_used,
        estimated_cost_inr=estimated_cost_inr,
    )
    db.add(log_entry)
    await db.flush()

    return {
        "status": "logged",
        "log_id": log_entry.id,
    }
