"""
Notification service — SSE broadcasting + optional WhatsApp alerts to seller.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages SSE event broadcasting to connected dashboard clients."""

    def __init__(self):
        # seller_id -> list of asyncio.Queue (one per connected SSE client)
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, seller_id: str) -> asyncio.Queue:
        """Register a new SSE client for a seller."""
        queue: asyncio.Queue = asyncio.Queue()
        if seller_id not in self._subscribers:
            self._subscribers[seller_id] = []
        self._subscribers[seller_id].append(queue)
        logger.info(f"SSE client subscribed for seller {seller_id}")
        return queue

    def unsubscribe(self, seller_id: str, queue: asyncio.Queue):
        """Remove an SSE client."""
        if seller_id in self._subscribers:
            self._subscribers[seller_id] = [
                q for q in self._subscribers[seller_id] if q is not queue
            ]
            if not self._subscribers[seller_id]:
                del self._subscribers[seller_id]

    async def push(self, seller_id: str, event: str, data: dict[str, Any]):
        """Push an event to all SSE clients for a seller."""
        if seller_id not in self._subscribers:
            return

        payload = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        dead_queues = []
        for queue in self._subscribers[seller_id]:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        # Clean up dead/full queues
        for q in dead_queues:
            self.unsubscribe(seller_id, q)

    async def push_new_escalation(self, seller_id: str, escalation_data: dict):
        await self.push(seller_id, "new_escalation", escalation_data)

    async def push_escalation_followup(self, seller_id: str, escalation_id: str, message: str):
        await self.push(seller_id, "escalation_followup", {
            "escalation_id": escalation_id,
            "message": message,
        })

    async def push_new_order(self, seller_id: str, order_data: dict):
        await self.push(seller_id, "new_order", order_data)

    async def push_order_status_change(self, seller_id: str, order_id: str, new_status: str):
        await self.push(seller_id, "order_status_change", {
            "order_id": order_id,
            "status": new_status,
        })

    async def push_new_message(self, seller_id: str, conversation_id: str, sender: str, preview: str):
        await self.push(seller_id, "new_message", {
            "conversation_id": conversation_id,
            "sender": sender,
            "preview": preview[:100],
        })

    async def push_low_stock(self, seller_id: str, product_id: str, product_name: str, stock: int):
        await self.push(seller_id, "low_stock_alert", {
            "product_id": product_id,
            "product_name": product_name,
            "stock_quantity": stock,
        })


# Singleton
notification_service = NotificationService()
