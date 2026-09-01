"""
Tool: search_inventory
Searches the product catalog with text matching and filters.
"""

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Product


async def search_inventory(
    db: AsyncSession,
    seller_id: str,
    query: str,
    filters: dict | None = None,
) -> dict:
    """
    Search live product catalog. Returns matching products with stock/price.
    Uses ILIKE for text matching across name, description, category, color, size.
    """
    filters = filters or {}

    conditions = [
        Product.seller_id == seller_id,
        Product.is_active == True,
    ]

    # Text search across multiple columns
    if query:
        search_term = f"%{query}%"
        conditions.append(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.category.ilike(search_term),
                Product.color.ilike(search_term),
                Product.size.ilike(search_term),
                Product.sku.ilike(search_term),
            )
        )

    # Structured filters
    if filters.get("category"):
        conditions.append(Product.category.ilike(f"%{filters['category']}%"))
    if filters.get("color"):
        conditions.append(Product.color.ilike(f"%{filters['color']}%"))
    if filters.get("size"):
        conditions.append(Product.size.ilike(f"%{filters['size']}%"))
    if filters.get("min_price") is not None:
        conditions.append(Product.price >= filters["min_price"])
    if filters.get("max_price") is not None:
        conditions.append(Product.price <= filters["max_price"])
    if filters.get("in_stock_only", True):
        conditions.append(Product.stock_quantity > 0)

    stmt = select(Product).where(and_(*conditions)).limit(10)
    result = await db.execute(stmt)
    products = result.scalars().all()

    return {
        "found": len(products),
        "products": [
            {
                "product_id": p.id,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "price": p.price,
                "size": p.size,
                "color": p.color,
                "sku": p.sku,
                "stock_quantity": p.stock_quantity,
                "image_url": p.image_url,
            }
            for p in products
        ],
    }
