import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price_nonnegative"),
        CheckConstraint("selling_price >= 0", name="ck_products_selling_price_nonnegative"),
        CheckConstraint("current_stock >= 0", name="ck_products_current_stock_nonnegative"),
        CheckConstraint("minimum_stock >= 0", name="ck_products_minimum_stock_nonnegative"),
        Index("ix_products_category_active", "category_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category: Mapped["Category"] = relationship(back_populates="products")  # noqa: F821
    sale_items: Mapped[list["SaleItem"]] = relationship(back_populates="product")  # noqa: F821
    inventory_movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="product")  # noqa: F821
