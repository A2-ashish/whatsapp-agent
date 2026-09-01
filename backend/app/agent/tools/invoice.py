"""
Tool: generate_invoice
Generates a formatted text invoice for a confirmed order.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Order, Customer


async def generate_invoice(
    db: AsyncSession,
    order_id: str,
) -> dict:
    """Generate a formatted text invoice for sending to the customer."""
    order = await db.get(Order, order_id)
    if not order:
        return {"status": "error", "message": "Order not found"}

    customer = await db.get(Customer, order.customer_id)

    # Build invoice text
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📋 *INVOICE*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"Order: #{order.id[:8]}",
        f"Date: {order.created_at.strftime('%d %b %Y') if order.created_at else 'N/A'}",
        f"Customer: {customer.name or customer.whatsapp_number if customer else 'N/A'}",
        "",
        "*Items:*",
    ]

    items = order.items_json if isinstance(order.items_json, list) else []
    for i, item in enumerate(items, 1):
        name = item.get("product_name", item.get("product_id", "Item"))
        qty = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0)
        line_total = item.get("line_total", qty * unit_price)
        lines.append(f"  {i}. {name} × {qty} @ ₹{unit_price} = ₹{line_total}")

    lines.extend([
        "",
        f"Subtotal: ₹{order.subtotal}",
    ])

    if order.discount_applied and order.discount_applied > 0:
        lines.append(f"Discount: -₹{order.discount_applied}")

    lines.extend([
        f"*Total: ₹{order.total}*",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "Thank you for your order! 🙏",
    ])

    invoice_text = "\n".join(lines)

    return {
        "status": "success",
        "order_id": order.id,
        "invoice_text": invoice_text,
        "message": "Invoice generated. Send this to the customer.",
    }
