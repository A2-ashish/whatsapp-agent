"""
SQLAlchemy ORM models for all 8 core tables.
Addresses all 6 architectural gaps from the review.
"""

import uuid
import hashlib
import json
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime,
    ForeignKey, JSON, Index, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ─── Sellers ──────────────────────────────────────────────────────────

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(String, primary_key=True, default=generate_uuid)
    business_name = Column(String(255), nullable=False)
    product_category = Column(String(255), nullable=False, default="general merchandise")
    phone_number = Column(String(20), nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    auto_approve_order_limit = Column(Float, nullable=False, default=25000.0)
    # WhatsApp Cloud API credentials
    wa_phone_number_id = Column(String(100), nullable=True)
    wa_access_token = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    products = relationship("Product", back_populates="seller", cascade="all, delete-orphan")
    discount_policies = relationship("DiscountPolicy", back_populates="seller", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="seller", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="seller", cascade="all, delete-orphan")


# ─── Products ─────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    size = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    sku = Column(String(100), nullable=True)
    stock_quantity = Column(Integer, nullable=False, default=0)
    image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    seller = relationship("Seller", back_populates="products")

    __table_args__ = (
        Index("ix_products_seller_active", "seller_id", "is_active"),
        Index("ix_products_name_category", "name", "category"),
    )


# ─── Discount Policy ──────────────────────────────────────────────────

class DiscountPolicy(Base):
    __tablename__ = "discount_policies"

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    min_quantity = Column(Integer, nullable=False)
    max_quantity = Column(Integer, nullable=True)  # NULL = no upper bound
    discount_percent = Column(Float, nullable=False)
    active_from = Column(DateTime(timezone=True), nullable=True)
    active_to = Column(DateTime(timezone=True), nullable=True)
    description = Column(String(255), nullable=True)  # e.g. "Festival sale"
    is_promotion = Column(Boolean, default=False)

    seller = relationship("Seller", back_populates="discount_policies")

    __table_args__ = (
        Index("ix_discount_seller_qty", "seller_id", "min_quantity"),
    )


# ─── Customers ─────────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    whatsapp_number = Column(String(20), nullable=False)
    name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)  # Owner's manual notes
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    seller = relationship("Seller", back_populates="customers")
    conversations = relationship("Conversation", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("seller_id", "whatsapp_number", name="uq_customer_seller_phone"),
        Index("ix_customer_phone", "whatsapp_number"),
    )


# ─── Conversations ────────────────────────────────────────────────────

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())
    # Gap #4: Track when customer last messaged for 24-hour window
    last_customer_message_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="active")  # active / closed
    # Gap #3: Pause state for escalation
    is_paused = Column(Boolean, default=False)
    paused_escalation_id = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    escalations = relationship("Escalation", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_conversation_customer", "customer_id"),
        Index("ix_conversation_seller_status", "seller_id", "status"),
    )


# ─── Messages ──────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), nullable=False)  # customer / agent / owner
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    # Tool call audit log for this message
    tool_calls_json = Column(JSON, nullable=True)
    # Gap: WhatsApp message dedup
    wa_message_id = Column(String(100), nullable=True, unique=True)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_message_conversation_time", "conversation_id", "timestamp"),
    )


# ─── Orders ────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    status = Column(String(20), default="pending")
    # pending / confirmed / processing / shipped / completed / cancelled
    items_json = Column(JSON, nullable=False)
    subtotal = Column(Float, nullable=False)
    discount_applied = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    # Gap #2: Conversation-scoped idempotency
    idempotency_key = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    seller = relationship("Seller", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")

    __table_args__ = (
        Index("ix_order_seller_status", "seller_id", "status"),
        Index("ix_order_customer", "customer_id"),
    )


# ─── Escalations ──────────────────────────────────────────────────────

class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=False)
    conversation_summary = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    status = Column(String(20), default="open")  # open / resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    # How it was resolved: instruct_agent / direct_reply / auto
    resolution_mode = Column(String(30), nullable=True)

    conversation = relationship("Conversation", back_populates="escalations")

    __table_args__ = (
        Index("ix_escalation_seller_status", "seller_id", "status"),
    )


# ─── Agent Action Log ─────────────────────────────────────────────────

class AgentActionLog(Base):
    __tablename__ = "agent_action_log"

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(100), nullable=False)
    details_json = Column(JSON, nullable=True)
    # Gap #6: Cost tracking
    tokens_used = Column(Integer, nullable=True)
    estimated_cost_inr = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_action_log_conversation", "conversation_id"),
        Index("ix_action_log_seller_time", "seller_id", "timestamp"),
    )


# ─── Helper: Generate idempotency key ─────────────────────────────────

def generate_idempotency_key(conversation_id: str, items: list, total: float) -> str:
    """
    Gap #2 fix: Conversation-scoped idempotency key.
    Same conversation + same items + same total = same key.
    A new conversation (e.g. after cancel-reorder) gets a different key.
    """
    payload = json.dumps({"conversation_id": conversation_id, "items": items, "total": total}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
