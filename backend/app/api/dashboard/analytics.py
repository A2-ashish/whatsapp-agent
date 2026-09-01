"""
Dashboard Analytics API — orders, revenue, escalations, autonomy rate, cost.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Seller, Order, Escalation, Conversation, AgentActionLog
from app.schemas import AnalyticsResponse
from app.api.dashboard.auth import get_current_seller_dep

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # Orders today
    result = await db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(Order.seller_id == seller.id, Order.created_at >= today_start)
    )
    row = result.one()
    orders_today = row[0]
    revenue_today = float(row[1])

    # Orders this week
    result = await db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(Order.seller_id == seller.id, Order.created_at >= week_start)
    )
    row = result.one()
    orders_this_week = row[0]
    revenue_this_week = float(row[1])

    # Open escalations
    result = await db.execute(
        select(func.count(Escalation.id))
        .where(Escalation.seller_id == seller.id, Escalation.status == "open")
    )
    open_escalations = result.scalar() or 0

    # Total conversations
    result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.seller_id == seller.id)
    )
    total_conversations = result.scalar() or 0

    # Autonomy rate: orders without escalation / total orders
    result = await db.execute(
        select(func.count(Order.id))
        .where(Order.seller_id == seller.id)
    )
    total_orders = result.scalar() or 0

    # Orders whose conversations had escalations
    result = await db.execute(
        select(func.count(func.distinct(Order.id)))
        .join(Escalation, and_(
            Escalation.conversation_id == Order.conversation_id,
            Escalation.seller_id == Order.seller_id,
        ))
        .where(Order.seller_id == seller.id)
    )
    escalated_orders = result.scalar() or 0

    autonomy_rate = 0.0
    if total_orders > 0:
        autonomy_rate = round(((total_orders - escalated_orders) / total_orders) * 100, 1)

    # Total agent cost
    result = await db.execute(
        select(func.coalesce(func.sum(AgentActionLog.estimated_cost_inr), 0))
        .where(AgentActionLog.seller_id == seller.id)
    )
    total_cost_inr = float(result.scalar() or 0)

    avg_cost_per_order = 0.0
    if total_orders > 0:
        avg_cost_per_order = round(total_cost_inr / total_orders, 2)

    return AnalyticsResponse(
        orders_today=orders_today,
        orders_this_week=orders_this_week,
        revenue_today=round(revenue_today, 2),
        revenue_this_week=round(revenue_this_week, 2),
        open_escalations=open_escalations,
        total_conversations=total_conversations,
        autonomy_rate=autonomy_rate,
        total_cost_inr=round(total_cost_inr, 4),
        avg_cost_per_order=avg_cost_per_order,
    )
