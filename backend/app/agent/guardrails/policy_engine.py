"""
Policy Engine — Server-side guardrail validation.
The prompt is guidance; this engine is law.
Every mutating tool call passes through here before commit.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Seller, Product, DiscountPolicy, Order

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Validates every create_order call server-side against:
    1. Order total ≤ seller's auto_approve_order_limit
    2. Discount applied ≤ active discount_policy tier
    3. Stock availability (informational — actual enforcement is atomic SQL)
    """

    async def validate_order_creation(
        self,
        db: AsyncSession,
        seller_id: str,
        customer_id: str,
        items: list[dict],
        total: float,
    ) -> dict:
        """Run all validation checks. Returns dict with approved/violation."""

        # 1. Order limit check
        seller = await db.get(Seller, seller_id)
        if not seller:
            return self._reject("Seller not found", "escalate")

        if total > seller.auto_approve_order_limit:
            return self._reject(
                f"Order total ₹{total} exceeds auto-approval limit of ₹{seller.auto_approve_order_limit}",
                "escalate",
                {"total": total, "limit": seller.auto_approve_order_limit},
            )

        # 2. Discount compliance check
        total_quantity = sum(item.get("quantity", 0) for item in items)
        max_allowed_discount = await self._get_max_discount(db, seller_id, total_quantity)

        # Calculate what discount is being applied
        subtotal = 0.0
        for item in items:
            product = await db.get(Product, item.get("product_id", ""))
            if product:
                subtotal += product.price * item.get("quantity", 0)

        if subtotal > 0:
            implied_discount_pct = ((subtotal - total) / subtotal) * 100
            if implied_discount_pct > max_allowed_discount + 0.5:  # 0.5% tolerance for rounding
                return self._reject(
                    f"Discount of {implied_discount_pct:.1f}% exceeds max allowed {max_allowed_discount}% for {total_quantity} units",
                    "escalate",
                    {
                        "implied_discount": round(implied_discount_pct, 1),
                        "max_allowed": max_allowed_discount,
                        "quantity": total_quantity,
                    },
                )

        # 3. Stock availability (pre-check — actual enforcement is the atomic UPDATE)
        stock_issues = []
        for item in items:
            product = await db.get(Product, item.get("product_id", ""))
            if not product:
                stock_issues.append(f"Product {item.get('product_id')} not found")
            elif item.get("quantity", 0) > product.stock_quantity:
                stock_issues.append(
                    f"{product.name}: need {item['quantity']}, have {product.stock_quantity}"
                )

        if stock_issues:
            return self._reject(
                "Insufficient stock",
                "inform_customer",
                {"issues": stock_issues},
            )

        return {"approved": True}

    async def _get_max_discount(
        self, db: AsyncSession, seller_id: str, quantity: int
    ) -> float:
        """Find maximum allowed discount percentage for a given quantity."""
        now = datetime.now(timezone.utc)

        stmt = select(DiscountPolicy).where(
            DiscountPolicy.seller_id == seller_id,
            DiscountPolicy.min_quantity <= quantity,
            or_(
                DiscountPolicy.max_quantity == None,
                DiscountPolicy.max_quantity >= quantity,
            ),
            or_(
                DiscountPolicy.active_from == None,
                DiscountPolicy.active_from <= now,
            ),
            or_(
                DiscountPolicy.active_to == None,
                DiscountPolicy.active_to >= now,
            ),
        )

        result = await db.execute(stmt)
        policies = result.scalars().all()

        if not policies:
            return 0.0

        return max(p.discount_percent for p in policies)

    def _reject(self, violation: str, required_action: str, details: dict | None = None) -> dict:
        logger.warning(f"Policy violation: {violation}")
        return {
            "approved": False,
            "violation": violation,
            "required_action": required_action,
            "details": details,
        }
