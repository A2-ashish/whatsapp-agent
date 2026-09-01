"""
Tool: get_customer_history
Retrieves past orders, preferences, and seller's notes about a customer.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Customer, Order


async def get_customer_history(
    db: AsyncSession,
    customer_id: str,
) -> dict:
    """Get a customer's history — past orders, notes, preferences."""
    customer = await db.get(Customer, customer_id)
    if not customer:
        return {"error": "Customer not found"}

    # Get past orders
    stmt = (
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    total_spent = sum(o.total for o in orders)
    avg_order_value = total_spent / len(orders) if orders else 0

    return {
        "customer_id": customer.id,
        "name": customer.name or "Unknown",
        "whatsapp_number": customer.whatsapp_number,
        "owner_notes": customer.notes or "No notes",
        "total_orders": len(orders),
        "total_spent": total_spent,
        "avg_order_value": round(avg_order_value, 2),
        "member_since": customer.created_at.isoformat() if customer.created_at else None,
        "recent_orders": [
            {
                "order_id": o.id,
                "status": o.status,
                "total": o.total,
                "items": o.items_json,
                "date": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders[:5]  # Last 5 orders
        ],
    }
