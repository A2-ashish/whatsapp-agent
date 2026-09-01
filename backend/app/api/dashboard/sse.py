"""
Dashboard SSE endpoint — real-time event stream for the seller dashboard.
"""

import asyncio
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Seller
from app.api.dashboard.auth import get_current_seller_dep
from app.services.notification_service import notification_service

router = APIRouter(prefix="/events", tags=["sse"])


@router.get("/")
async def event_stream(
    seller: Seller = Depends(get_current_seller_dep),
):
    """
    SSE endpoint. Dashboard connects here for real-time updates.
    Events: new_escalation, new_order, order_status_change,
    escalation_followup, low_stock_alert, new_message.
    """
    queue = notification_service.subscribe(seller.id)

    async def generate():
        try:
            # Send a keepalive ping every 30 seconds
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "update", "data": data}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            notification_service.unsubscribe(seller.id, queue)

    return EventSourceResponse(generate())
