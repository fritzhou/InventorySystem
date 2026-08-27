import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.expense import ExpenseStatus


def _text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    _name = field_validator("name")(_text)


class ExpenseCategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if value is None:
            raise ValueError("must not be null")
        return _text(value)


class ExpenseCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExpenseCreate(BaseModel):
    category_id: uuid.UUID
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    expense_date: date
    notes: str | None = None
    _description = field_validator("description")(_text)


class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: uuid.UUID | None = None
    description: str | None = Field(None, min_length=1, max_length=255)
    amount: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    expense_date: date | None = None
    notes: str | None = None

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, value):
        if value is None:
            raise ValueError("must not be null")
        return _text(value)

    @field_validator("category_id", "amount", "expense_date")
    @classmethod
    def required_fields_not_null(cls, value):
        if value is None:
            raise ValueError("must not be null")
        return value


class ExpenseVoid(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    _reason = field_validator("reason")(_text)


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    expense_number: str
    category_id: uuid.UUID
    category_name: str
    description: str
    amount: Decimal
    expense_date: date
    notes: str | None
    status: ExpenseStatus
    created_at: datetime
    updated_at: datetime
    voided_at: datetime | None
    void_reason: str | None


class ExpensePage(BaseModel):
    items: list[ExpenseRead]
    total: int
    page: int
    page_size: int
    pages: int
