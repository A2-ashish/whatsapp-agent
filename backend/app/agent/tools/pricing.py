"""
Tools: get_discount_policy, calculate_order_total
Pricing logic with discount tier enforcement.
"""

from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import DiscountPolicy, Product


async def get_discount_policy(
    db: AsyncSession,
    seller_id: str,
) -> dict:
    """Get current active discount tiers and promotions."""
    now = datetime.now(timezone.utc)

    stmt = select(DiscountPolicy).where(
        DiscountPolicy.seller_id == seller_id,
        or_(
            DiscountPolicy.active_from == None,
            DiscountPolicy.active_from <= now,
        ),
        or_(
            DiscountPolicy.active_to == None,
            DiscountPolicy.active_to >= now,
        ),
    ).order_by(DiscountPolicy.min_quantity)

    result = await db.execute(stmt)
    policies = result.scalars().all()

    tiers = []
    promotions = []

    for p in policies:
        entry = {
            "id": p.id,
            "min_quantity": p.min_quantity,
            "max_quantity": p.max_quantity,
            "discount_percent": p.discount_percent,
            "description": p.description,
        }
        if p.is_promotion:
            promotions.append(entry)
        else:
            tiers.append(entry)

    return {
        "discount_tiers": tiers,
        "active_promotions": promotions,
        "note": "Apply the tier where item quantity falls within min/max range. Do not invent discounts outside these tiers.",
    }


def _find_applicable_discount(tiers: list[dict], quantity: int) -> float:
    """Find the discount percentage for a given quantity from the tiers."""
    applicable = 0.0
    for tier in tiers:
        if quantity >= tier["min_quantity"]:
            if tier["max_quantity"] is None or quantity <= tier["max_quantity"]:
                applicable = max(applicable, tier["discount_percent"])
    return applicable


async def calculate_order_total(
    db: AsyncSession,
    seller_id: str,
    items: list[dict],
    customer_id: str,
    discount_override: float | None = None,
) -> dict:
    """
    Calculate order total with proper pricing and discount application.
    Items format: [{"product_id": "...", "quantity": N}, ...]
    """
    # Fetch products
    product_ids = [item["product_id"] for item in items]
    stmt = select(Product).where(
        Product.id.in_(product_ids),
        Product.seller_id == seller_id,
    )
    result = await db.execute(stmt)
    products = {p.id: p for p in result.scalars().all()}

    # Fetch discount policy
    policy_data = await get_discount_policy(db, seller_id)

    line_items = []
    subtotal = 0.0
    issues = []

    for item in items:
        product = products.get(item["product_id"])
        if not product:
            issues.append(f"Product {item['product_id']} not found")
            continue

        qty = item["quantity"]
        if qty > product.stock_quantity:
            issues.append(
                f"{product.name}: requested {qty} but only {product.stock_quantity} in stock"
            )

        line_total = product.price * qty
        subtotal += line_total
        line_items.append({
            "product_id": product.id,
            "name": product.name,
            "quantity": qty,
            "unit_price": product.price,
            "line_total": line_total,
            "stock_available": product.stock_quantity,
        })

    # Calculate discount
    total_quantity = sum(item["quantity"] for item in items)
    if discount_override is not None:
        discount_pct = discount_override
    else:
        discount_pct = _find_applicable_discount(policy_data["discount_tiers"], total_quantity)

    discount_amount = subtotal * (discount_pct / 100)
    total = subtotal - discount_amount

    return {
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "total_quantity": total_quantity,
        "discount_percent": discount_pct,
        "discount_amount": round(discount_amount, 2),
        "total": round(total, 2),
        "issues": issues if issues else None,
        "note": f"Discount of {discount_pct}% applied for {total_quantity} units." if discount_pct > 0 else "No bulk discount applicable at this quantity.",
    }
