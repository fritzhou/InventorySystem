import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.inventory_movement import MovementType


class StockAdjustmentCreate(BaseModel):
    type: MovementType
    quantity: int | None = Field(default=None, gt=0)
    actual_stock: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_action(self):
        if self.type not in {MovementType.RESTOCK, MovementType.DAMAGE, MovementType.CORRECTION}:
            raise ValueError("Manual adjustments must be RESTOCK, DAMAGE, or CORRECTION.")
        if self.type == MovementType.CORRECTION:
            if self.actual_stock is None or self.quantity is not None:
                raise ValueError("Correction requires actual_stock and does not accept quantity.")
        elif self.quantity is None or self.actual_stock is not None:
            raise ValueError("Restock and damage require quantity and do not accept actual_stock.")
        self.note = self.note.strip() or None if self.note is not None else None
        return self


class MovementProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    sku: str
    is_active: bool


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    movement_type: MovementType
    quantity_change: int
    stock_before: int
    stock_after: int
    reference_type: str | None
    reference_id: uuid.UUID | None
    note: str | None
    created_at: datetime
    product: MovementProduct
    receipt_number: str | None = None
    po_number: str | None = None


class InventoryMovementPage(BaseModel):
    items: list[InventoryMovementRead]
    page: int
    page_size: int
    total_items: int
    total_pages: int
