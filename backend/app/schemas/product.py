import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: uuid.UUID
    cost_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    current_stock: int = Field(default=0, ge=0)
    minimum_stock: int = Field(default=0, ge=0)

    @field_validator("name", "sku")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: uuid.UUID | None = None
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    minimum_stock: int | None = Field(default=None, ge=0)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
