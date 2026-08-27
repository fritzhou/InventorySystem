import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CheckoutItem(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)


class CheckoutCreate(BaseModel):
    items: list[CheckoutItem] = Field(min_length=1)
    amount_tendered: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_number: str
    subtotal: Decimal
    total: Decimal
    amount_tendered: Decimal
    change_due: Decimal
    payment_method: str
    created_at: datetime
    items: list[SaleItemRead]
