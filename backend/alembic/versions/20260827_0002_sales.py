"""Add sales and sale item snapshots.

Revision ID: 20260827_0002
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_0002"
down_revision: str | None = "20260827_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("receipt_number", sa.String(40), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_tendered", sa.Numeric(12, 2), nullable=False),
        sa.Column("change_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("subtotal >= 0", name="ck_sales_subtotal_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_sales_total_nonnegative"),
        sa.CheckConstraint("amount_tendered >= total", name="ck_sales_tendered_covers_total"),
        sa.CheckConstraint("change_due >= 0", name="ck_sales_change_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_receipt_number", "sales", ["receipt_number"], unique=True)
    op.create_table(
        "sale_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(160), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_items_unit_price_nonnegative"),
        sa.CheckConstraint("quantity > 0", name="ck_sale_items_quantity_positive"),
        sa.CheckConstraint("line_total >= 0", name="ck_sale_items_line_total_nonnegative"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"])
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"])


def downgrade() -> None:
    op.drop_table("sale_items")
    op.drop_table("sales")
