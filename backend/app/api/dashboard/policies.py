"""
Dashboard Discount Policies API — CRUD for discount tiers + seller settings.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Seller, DiscountPolicy
from app.schemas import DiscountPolicyCreate, DiscountPolicyResponse, SellerSettingsUpdate
from app.api.dashboard.auth import get_current_seller_dep

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/discounts", response_model=list[DiscountPolicyResponse])
async def list_discount_policies(
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DiscountPolicy)
        .where(DiscountPolicy.seller_id == seller.id)
        .order_by(DiscountPolicy.min_quantity)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/discounts", response_model=DiscountPolicyResponse, status_code=201)
async def create_discount_policy(
    policy: DiscountPolicyCreate,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    db_policy = DiscountPolicy(seller_id=seller.id, **policy.model_dump())
    db.add(db_policy)
    await db.flush()
    await db.refresh(db_policy)
    return db_policy


@router.delete("/discounts/{policy_id}", status_code=204)
async def delete_discount_policy(
    policy_id: str,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(DiscountPolicy, policy_id)
    if not policy or policy.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(policy)
    await db.flush()


@router.get("/settings")
async def get_seller_settings(
    seller: Seller = Depends(get_current_seller_dep),
):
    return {
        "auto_approve_order_limit": seller.auto_approve_order_limit,
        "business_name": seller.business_name,
        "product_category": seller.product_category,
        "phone_number": seller.phone_number,
    }


@router.patch("/settings")
async def update_seller_settings(
    updates: SellerSettingsUpdate,
    seller: Seller = Depends(get_current_seller_dep),
    db: AsyncSession = Depends(get_db),
):
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(seller, key, value)
    await db.flush()

    return {
        "auto_approve_order_limit": seller.auto_approve_order_limit,
        "business_name": seller.business_name,
        "product_category": seller.product_category,
        "phone_number": seller.phone_number,
    }
