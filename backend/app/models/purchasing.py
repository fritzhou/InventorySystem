import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class PurchaseOrderStatus(str, enum.Enum):
    DRAFT="DRAFT"; ORDERED="ORDERED"; PARTIALLY_RECEIVED="PARTIALLY_RECEIVED"; RECEIVED="RECEIVED"; CANCELLED="CANCELLED"

class Supplier(Base):
    __tablename__="suppliers"
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]=mapped_column(String(160), index=True)
    contact_person: Mapped[str|None]=mapped_column(String(160)); phone: Mapped[str|None]=mapped_column(String(50)); email: Mapped[str|None]=mapped_column(String(254))
    address: Mapped[str|None]=mapped_column(Text); notes: Mapped[str|None]=mapped_column(Text)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    purchase_orders: Mapped[list["PurchaseOrder"]]=relationship(back_populates="supplier")

class PurchaseOrder(Base):
    __tablename__="purchase_orders"
    __table_args__=(Index("ix_purchase_orders_order_date", "order_date"),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4)
    po_number: Mapped[str]=mapped_column(String(40), unique=True, index=True)
    supplier_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    status: Mapped[PurchaseOrderStatus]=mapped_column(Enum(PurchaseOrderStatus, native_enum=False, length=24), default=PurchaseOrderStatus.DRAFT, index=True)
    order_date: Mapped[date]=mapped_column(Date, default=date.today); expected_date: Mapped[date|None]=mapped_column(Date)
    notes: Mapped[str|None]=mapped_column(Text); subtotal: Mapped[Decimal]=mapped_column(Numeric(12,2))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    supplier: Mapped[Supplier]=relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]]=relationship(back_populates="purchase_order", cascade="all, delete-orphan")

class PurchaseOrderItem(Base):
    __tablename__="purchase_order_items"
    __table_args__=(CheckConstraint("ordered_quantity > 0"), CheckConstraint("received_quantity >= 0 AND received_quantity <= ordered_quantity"), CheckConstraint("unit_cost >= 0"), Index("ix_po_items_po", "purchase_order_id"))
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    product_name: Mapped[str]=mapped_column(String(160)); sku: Mapped[str]=mapped_column(String(64))
    ordered_quantity: Mapped[int]=mapped_column(Integer); received_quantity: Mapped[int]=mapped_column(Integer, default=0)
    unit_cost: Mapped[Decimal]=mapped_column(Numeric(12,2)); line_total: Mapped[Decimal]=mapped_column(Numeric(12,2))
    purchase_order: Mapped[PurchaseOrder]=relationship(back_populates="items")
    product: Mapped["Product"]=relationship()  # noqa: F821
