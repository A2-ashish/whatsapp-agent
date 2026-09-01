"""
Dashboard Auth API — JWT-based seller login.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
from jose import jwt

from app.config import get_settings
from app.db.database import get_db
from app.db.models import Seller
from app.schemas import LoginRequest, LoginResponse, SellerProfile

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


def create_access_token(seller_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    payload = {"sub": seller_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def get_current_seller(
    request=None,
    db: AsyncSession = Depends(get_db),
    token: str = None,
) -> Seller:
    """Extract seller from JWT token."""
    from fastapi import Request
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    # This will be used as a dependency
    pass


# Simpler auth dependency
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

security = HTTPBearer()


async def get_current_seller_dep(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> Seller:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        seller_id = payload.get("sub")
        if not seller_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        seller = await db.get(Seller, seller_id)
        if not seller:
            raise HTTPException(status_code=401, detail="Seller not found")

        return seller
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Seller).where(Seller.email == req.email)
    result = await db.execute(stmt)
    seller = result.scalar_one_or_none()

    if not seller or not verify_password(req.password, seller.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(seller.id)
    return LoginResponse(
        access_token=token,
        seller_id=seller.id,
        business_name=seller.business_name,
    )


@router.get("/me", response_model=SellerProfile)
async def get_me(seller: Seller = Depends(get_current_seller_dep)):
    return SellerProfile(
        id=seller.id,
        business_name=seller.business_name,
        product_category=seller.product_category,
        email=seller.email,
        phone_number=seller.phone_number,
        auto_approve_order_limit=seller.auto_approve_order_limit,
    )
