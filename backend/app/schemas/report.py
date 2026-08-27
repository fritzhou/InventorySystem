from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ReportSummary(BaseModel):
    sales_total: Decimal
    transaction_count: int
    items_sold: int
    gross_profit: Decimal
    profit_complete: bool
    average_transaction_value: Decimal
    total_active_products: int
    total_units_in_stock: int
    low_stock_count: int
    out_of_stock_count: int


class SalesTrendPoint(BaseModel):
    date: date
    sales: Decimal
    transactions: int
    items_sold: int


class TopProduct(BaseModel):
    product_id: UUID | None
    product_name: str
    sku: str
    quantity_sold: int
    revenue: Decimal


class StockProduct(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    current_stock: int
    minimum_stock: int


class InventoryStatus(BaseModel):
    total_active_products: int
    total_units_in_stock: int
    low_stock: list[StockProduct]
    out_of_stock: list[StockProduct]
