import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReturnItemCreate(BaseModel):
    sale_item_id: uuid.UUID
    quantity: int = Field(gt=0)
    return_to_stock: bool = False


class SaleReturnCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
    items: list[ReturnItemCreate] = Field(min_length=1)


class ReturnItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sale_item_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    unit_price: Decimal
    cost_price: Decimal | None
    quantity: int
    refund_amount: Decimal
    return_to_stock: bool


class SaleReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    receipt_number: str


class SaleReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    return_number: str
    sale_id: uuid.UUID
    refund_total: Decimal
    reason: str | None
    created_at: datetime
    items: list[ReturnItemRead]
    sale: SaleReference


class ReturnsPage(BaseModel):
    items: list[SaleReturnRead]
    page: int
    page_size: int
    total_items: int
    total_pages: int
