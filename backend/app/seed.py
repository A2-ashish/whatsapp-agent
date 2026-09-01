"""
Seed script — creates initial seller account and sample products.
Run with: uv run python -m app.seed
"""

import asyncio
from passlib.hash import bcrypt
from app.db.database import async_session_factory, engine
from app.db.models import Base, Seller, Product, DiscountPolicy
from app.config import get_settings

settings = get_settings()


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Check if seller already exists
        from sqlalchemy import select
        result = await db.execute(select(Seller).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # Create seller
        seller = Seller(
            business_name=settings.DEFAULT_BUSINESS_NAME,
            product_category=settings.DEFAULT_PRODUCT_CATEGORY,
            email="admin@store.com",
            password_hash=bcrypt.hash("admin123"),
            auto_approve_order_limit=settings.DEFAULT_AUTO_APPROVE_LIMIT,
            phone_number="+91XXXXXXXXXX",
            wa_phone_number_id=settings.WA_PHONE_NUMBER_ID or "",
            wa_access_token=settings.WA_ACCESS_TOKEN or "",
        )
        db.add(seller)
        await db.flush()

        # Sample products
        products = [
            Product(seller_id=seller.id, name="Premium Blue Formal Shirt", category="Shirts", description="Cotton blend formal shirt, slim fit", price=1299, size="M,L,XL", color="Blue", sku="SH-BLU-001", stock_quantity=50, is_active=True),
            Product(seller_id=seller.id, name="Classic White Formal Shirt", category="Shirts", description="Pure cotton formal shirt", price=1199, size="S,M,L,XL", color="White", sku="SH-WHT-001", stock_quantity=75, is_active=True),
            Product(seller_id=seller.id, name="Black Casual T-Shirt", category="T-Shirts", description="Round neck cotton t-shirt", price=599, size="M,L,XL,XXL", color="Black", sku="TS-BLK-001", stock_quantity=100, is_active=True),
            Product(seller_id=seller.id, name="Navy Polo T-Shirt", category="T-Shirts", description="Collar polo, pique cotton", price=899, size="M,L,XL", color="Navy", sku="TS-NAV-001", stock_quantity=60, is_active=True),
            Product(seller_id=seller.id, name="Beige Formal Trousers", category="Trousers", description="Pleated formal trousers", price=1599, size="30,32,34,36", color="Beige", sku="TR-BEG-001", stock_quantity=40, is_active=True),
            Product(seller_id=seller.id, name="Dark Grey Slim Jeans", category="Jeans", description="Stretch denim, slim fit", price=1899, size="30,32,34,36", color="Dark Grey", sku="JN-GRY-001", stock_quantity=35, is_active=True),
            Product(seller_id=seller.id, name="Printed Kurta Set", category="Ethnic", description="Cotton kurta with pyjama set", price=2499, size="M,L,XL,XXL", color="Maroon", sku="KS-MRN-001", stock_quantity=25, is_active=True),
            Product(seller_id=seller.id, name="Lightweight Linen Shirt", category="Shirts", description="Pure linen casual shirt", price=1799, size="M,L,XL", color="Olive Green", sku="SH-OLV-001", stock_quantity=30, is_active=True),
        ]
        db.add_all(products)

        # Discount policies
        policies = [
            DiscountPolicy(seller_id=seller.id, min_quantity=10, max_quantity=49, discount_percent=3, description="Small bulk: 10-49 units"),
            DiscountPolicy(seller_id=seller.id, min_quantity=50, max_quantity=99, discount_percent=5, description="Medium bulk: 50-99 units"),
            DiscountPolicy(seller_id=seller.id, min_quantity=100, max_quantity=199, discount_percent=8, description="Large bulk: 100-199 units"),
            DiscountPolicy(seller_id=seller.id, min_quantity=200, max_quantity=None, discount_percent=12, description="Wholesale: 200+ units"),
        ]
        db.add_all(policies)

        await db.commit()
        print(f"✅ Seeded: seller '{seller.business_name}' ({seller.email}), {len(products)} products, {len(policies)} discount tiers")
        print(f"   Login: admin@store.com / admin123")
        print(f"   Seller ID: {seller.id}")


if __name__ == "__main__":
    asyncio.run(seed())
