"""
Customer service — lookup, auto-creation on first WhatsApp contact.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Customer


class CustomerService:

    async def get_or_create(
        self, db: AsyncSession, seller_id: str, whatsapp_number: str
    ) -> tuple[Customer, bool]:
        """
        Look up customer by phone number. Create if first contact.
        Returns (customer, is_new).
        """
        stmt = select(Customer).where(
            Customer.seller_id == seller_id,
            Customer.whatsapp_number == whatsapp_number,
        )
        result = await db.execute(stmt)
        customer = result.scalar_one_or_none()

        if customer:
            return customer, False

        customer = Customer(
            seller_id=seller_id,
            whatsapp_number=whatsapp_number,
        )
        db.add(customer)
        await db.flush()
        return customer, True

    async def get_by_id(self, db: AsyncSession, customer_id: str) -> Customer | None:
        return await db.get(Customer, customer_id)

    async def update_name(self, db: AsyncSession, customer_id: str, name: str):
        customer = await db.get(Customer, customer_id)
        if customer:
            customer.name = name
            await db.flush()

    async def update_notes(self, db: AsyncSession, customer_id: str, notes: str):
        customer = await db.get(Customer, customer_id)
        if customer:
            customer.notes = notes
            await db.flush()


customer_service = CustomerService()
