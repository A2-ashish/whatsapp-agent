"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── Auth ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    seller_id: str
    business_name: str


class SellerProfile(BaseModel):
    id: str
    business_name: str
    product_category: str
    email: str
    phone_number: Optional[str] = None
    auto_approve_order_limit: float


# ─── Products ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float
    size: Optional[str] = None
    color: Optional[str] = None
    sku: Optional[str] = None
    stock_quantity: int = 0
    image_url: Optional[str] = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    size: Optional[str] = None
    color: Optional[str] = None
    sku: Optional[str] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    category: Optional[str]
    description: Optional[str]
    price: float
    size: Optional[str]
    color: Optional[str]
    sku: Optional[str]
    stock_quantity: int
    image_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Orders ────────────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    status: str  # confirmed / processing / shipped / completed / cancelled


class OrderResponse(BaseModel):
    id: str
    seller_id: str
    customer_id: str
    conversation_id: Optional[str]
    status: str
    items_json: list | dict
    subtotal: float
    discount_applied: float
    total: float
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Escalations ──────────────────────────────────────────────────────

class EscalationResolve(BaseModel):
    mode: str  # "instruct_agent" or "direct_reply"
    content: str  # The instruction or the message to send


class EscalationResponse(BaseModel):
    id: str
    seller_id: str
    customer_id: str
    conversation_id: str
    reason: str
    conversation_summary: Optional[str]
    suggested_action: Optional[str]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    resolution_mode: Optional[str]

    model_config = {"from_attributes": True}


# ─── Discount Policy ──────────────────────────────────────────────────

class DiscountPolicyCreate(BaseModel):
    min_quantity: int
    max_quantity: Optional[int] = None
    discount_percent: float
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None
    description: Optional[str] = None
    is_promotion: bool = False


class DiscountPolicyResponse(BaseModel):
    id: str
    min_quantity: int
    max_quantity: Optional[int]
    discount_percent: float
    active_from: Optional[datetime]
    active_to: Optional[datetime]
    description: Optional[str]
    is_promotion: bool

    model_config = {"from_attributes": True}


# ─── Conversations & Messages ──────────────────────────────────────────

class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    timestamp: datetime
    tool_calls_json: Optional[dict | list] = None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    customer_id: str
    status: str
    is_paused: bool
    started_at: datetime
    last_message_at: datetime
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Analytics ─────────────────────────────────────────────────────────

class AnalyticsResponse(BaseModel):
    orders_today: int
    orders_this_week: int
    revenue_today: float
    revenue_this_week: float
    open_escalations: int
    total_conversations: int
    autonomy_rate: float  # % of orders without escalation
    total_cost_inr: float  # Agent API cost
    avg_cost_per_order: float


# ─── Seller Settings ───────────────────────────────────────────────────

class SellerSettingsUpdate(BaseModel):
    business_name: Optional[str] = None
    product_category: Optional[str] = None
    auto_approve_order_limit: Optional[float] = None
    phone_number: Optional[str] = None
