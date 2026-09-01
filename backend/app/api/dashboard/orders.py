"""
Dashboard Orders API — list, detail, status update.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.database import get_db
from app.db.models import Seller, Order, Customer, Message, Conversation
from app.schemas import OrderResponse, OrderStatusUpdate
from app.api.dashboard.auth import get_current_seller_dep
from app.services.notification_service import notification_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    status: str | None = None,
    customer_id: str | None = None,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Order.seller_id == seller.id]
    if status:
        conditions.append(Order.status == status)
    if customer_id:
        conditions.append(Order.customer_id == customer_id)

    stmt = select(Order).where(*conditions).order_by(Order.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{order_id}")
async def get_order_detail(
    order_id: str,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")

    # Get customer info
    customer = await db.get(Customer, order.customer_id)

    # Get conversation transcript if linked
    transcript = []
    if order.conversation_id:
        stmt = (
            select(Message)
            .where(Message.conversation_id == order.conversation_id)
            .order_by(Message.timestamp)
        )
        result = await db.execute(stmt)
        transcript = [
            {
                "sender": m.sender,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "tool_calls": m.tool_calls_json,
            }
            for m in result.scalars().all()
        ]

    return {
        "order": {
            "id": order.id,
            "status": order.status,
            "items_json": order.items_json,
            "subtotal": order.subtotal,
            "discount_applied": order.discount_applied,
            "total": order.total,
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        },
        "customer": {
            "id": customer.id if customer else None,
            "name": customer.name if customer else None,
            "whatsapp_number": customer.whatsapp_number if customer else None,
            "notes": customer.notes if customer else None,
        },
        "conversation_transcript": transcript,
    }


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    valid_statuses = {"confirmed", "processing", "shipped", "completed", "cancelled"}
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    order = await db.get(Order, order_id)
    if not order or order.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status_update.status
    await db.flush()
    await db.refresh(order)

    # Notify dashboard
    await notification_service.push_order_status_change(
        seller.id, order.id, order.status
    )

    return order
