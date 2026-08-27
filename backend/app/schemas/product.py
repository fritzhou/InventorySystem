import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


def normalize_optional_barcode(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


class ProductBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
        return normalize_required_text(value)

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str | None) -> str | None:
        return normalize_optional_barcode(value)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: uuid.UUID | None = None
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    minimum_stock: int | None = Field(default=None, ge=0)

    @field_validator("name", "sku")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return normalize_required_text(value) if value is not None else None

    @field_validator("barcode")
    @classmethod
    def normalize_barcode(cls, value: str | None) -> str | None:
        return normalize_optional_barcode(value)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductSafeRead(BaseModel):
    """Operational product fields safe for cashier clients."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    sku: str
    barcode: str | None
    selling_price: Decimal
    current_stock: int
    minimum_stock: int
    is_active: bool


class ExternalProductRead(BaseModel):
    barcode: str
    product_name: str | None = None
    brand: str | None = None
    category_text: str | None = None
    package_size: str | None = None
    image_url: str | None = None


class ProductLookupRead(BaseModel):
    found: bool
    source: str
    product: ProductRead | None = None
    external_product: ExternalProductRead | None = None
    reason: str | None = None


class ProductLookupSafeRead(BaseModel):
    found: bool
    source: str
    product: ProductSafeRead | None = None
    external_product: ExternalProductRead | None = None
    reason: str | None = None
