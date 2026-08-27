import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovementType(str, enum.Enum):
    RESTOCK = "RESTOCK"
    SALE = "SALE"
    DAMAGE = "DAMAGE"
    CORRECTION = "CORRECTION"
    RETURN = "RETURN"


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("stock_before >= 0", name="ck_inventory_movements_stock_before_nonnegative"),
        CheckConstraint("stock_after >= 0", name="ck_inventory_movements_stock_after_nonnegative"),
        Index("ix_inventory_movements_product_id", "product_id"),
        Index("ix_inventory_movements_created_at", "created_at"),
        Index("ix_inventory_movements_reference_id", "reference_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType, native_enum=False, length=20))
    quantity_change: Mapped[int] = mapped_column(Integer)
    stock_before: Mapped[int] = mapped_column(Integer)
    stock_after: Mapped[int] = mapped_column(Integer)
    reference_type: Mapped[str | None] = mapped_column(String(30))
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="inventory_movements")  # noqa: F821
