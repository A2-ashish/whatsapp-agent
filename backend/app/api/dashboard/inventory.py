"""
Dashboard Inventory API — CRUD for products.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Seller, Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.api.dashboard.auth import get_current_seller_dep

router = APIRouter(prefix="/products", tags=["inventory"])


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    category: str | None = None,
    active_only: bool = False,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    conditions = [Product.seller_id == seller.id]
    if category:
        conditions.append(Product.category.ilike(f"%{category}%"))
    if active_only:
        conditions.append(Product.is_active == True)

    stmt = select(Product).where(*conditions).order_by(Product.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    db_product = Product(seller_id=seller.id, **product.model_dump())
    db.add(db_product)
    await db.flush()
    await db.refresh(db_product)
    return db_product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product or product.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    updates: ProductUpdate,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product or product.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product or product.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.flush()
