"""
Tools: create_order, check_order_status
Order creation with atomic stock decrement (Gap #1) and idempotency (Gap #2).
"""

import logging
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Order, Product, generate_idempotency_key
from app.agent.guardrails.policy_engine import PolicyEngine
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
policy_engine = PolicyEngine()


async def create_order(
    db: AsyncSession,
    seller_id: str,
    customer_id: str,
    conversation_id: str,
    items: list[dict],
    total: float,
    notes: str | None = None,
) -> dict:
    """
    Create an order with:
    - Gap #1: Atomic conditional stock decrement (no race condition)
    - Gap #2: Conversation-scoped idempotency key
    - Server-side policy engine validation
    """
    # ─── Gap #2: Idempotency check ────────────────────────────────
    idempotency_key = generate_idempotency_key(conversation_id, items, total)

    existing = await db.execute(
        select(Order).where(Order.idempotency_key == idempotency_key)
    )
    existing_order = existing.scalar_one_or_none()
    if existing_order:
        return {
            "status": "duplicate_prevented",
            "order_id": existing_order.id,
            "message": "This order was already created. Returning existing order.",
        }

    # ─── Server-side policy validation ─────────────────────────────
    validation = await policy_engine.validate_order_creation(
        db=db,
        seller_id=seller_id,
        customer_id=customer_id,
        items=items,
        total=total,
    )

    if not validation["approved"]:
        return {
            "status": "rejected",
            "reason": validation["violation"],
            "required_action": validation["required_action"],
            "details": validation.get("details"),
            "message": f"Order rejected by policy engine: {validation['violation']}. You must escalate this to the owner.",
        }

    # ─── Gap #1: Atomic stock decrement ────────────────────────────
    # Single UPDATE that decrements AND checks availability atomically.
    # If rowcount == 0, someone else got the stock first.
    stock_decrements_ok = True
    stock_issues = []

    for item in items:
        result = await db.execute(
            text("""
                UPDATE products
                SET stock_quantity = stock_quantity - :qty,
                    updated_at = NOW()
                WHERE id = :product_id
                  AND seller_id = :seller_id
                  AND stock_quantity >= :qty
            """),
            {
                "qty": item["quantity"],
                "product_id": item["product_id"],
                "seller_id": seller_id,
            },
        )
        if result.rowcount == 0:
            stock_decrements_ok = False
            stock_issues.append(
                f"Product {item.get('product_id')}: insufficient stock (concurrent order may have claimed it)"
            )

    if not stock_decrements_ok:
        # Rollback will undo any partial decrements
        return {
            "status": "rejected",
            "reason": "stock_unavailable",
            "required_action": "inform_customer",
            "details": stock_issues,
            "message": "Some items are no longer available. Inform the customer and suggest alternatives.",
        }

    # ─── Calculate subtotal and discount ───────────────────────────
    subtotal = 0.0
    items_with_prices = []
    for item in items:
        product = await db.get(Product, item["product_id"])
        unit_price = item.get("unit_price", product.price if product else 0)
        line_total = unit_price * item["quantity"]
        subtotal += line_total
        items_with_prices.append({
            "product_id": item["product_id"],
            "product_name": product.name if product else "Unknown",
            "quantity": item["quantity"],
            "unit_price": unit_price,
            "line_total": line_total,
        })

    discount_applied = max(0, subtotal - total)

    # ─── Create the order ──────────────────────────────────────────
    order = Order(
        seller_id=seller_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status="confirmed",
        items_json=items_with_prices,
        subtotal=round(subtotal, 2),
        discount_applied=round(discount_applied, 2),
        total=round(total, 2),
        notes=notes,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    await db.flush()

    # Check for low stock alerts
    for item in items:
        product = await db.get(Product, item["product_id"])
        if product and product.stock_quantity <= 5:
            await notification_service.push_low_stock(
                seller_id, product.id, product.name, product.stock_quantity
            )

    # Notify dashboard
    await notification_service.push_new_order(seller_id, {
        "order_id": order.id,
        "customer_id": customer_id,
        "total": order.total,
        "items_count": len(items),
        "status": order.status,
    })

    logger.info(f"Order {order.id} created: ₹{order.total} for customer {customer_id}")

    return {
        "status": "success",
        "order_id": order.id,
        "total": order.total,
        "discount_applied": order.discount_applied,
        "items": items_with_prices,
        "message": f"Order #{order.id[:8]} confirmed! Total: ₹{order.total}",
    }


async def check_order_status(
    db: AsyncSession,
    order_id: str | None = None,
    customer_id: str | None = None,
) -> dict:
    """Look up order status by order ID or customer's recent orders."""
    if order_id:
        order = await db.get(Order, order_id)
        if not order:
            return {"status": "not_found", "message": "Order not found"}
        return {
            "order_id": order.id,
            "status": order.status,
            "total": order.total,
            "items": order.items_json,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }

    if customer_id:
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        orders = result.scalars().all()

        if not orders:
            return {"status": "no_orders", "message": "No orders found for this customer"}

        return {
            "orders": [
                {
                    "order_id": o.id,
                    "status": o.status,
                    "total": o.total,
                    "items": o.items_json,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ]
        }

    return {"status": "error", "message": "Provide either order_id or customer_id"}
