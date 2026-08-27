"""sale returns and customer return inventory movements

Revision ID: 20260827_0007
Revises: 20260827_0006
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_0007"
down_revision = "20260827_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sale_returns",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("return_number", sa.String(40), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False), sa.Column("refund_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("refund_total >= 0", name="ck_sale_returns_refund_nonnegative"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("return_number"))
    op.create_index("ix_sale_returns_return_number", "sale_returns", ["return_number"], unique=True)
    op.create_index("ix_sale_returns_sale_id", "sale_returns", ["sale_id"])
    op.create_index("ix_sale_returns_created_at", "sale_returns", ["created_at"])
    op.create_table("sale_return_items",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("sale_return_id", sa.Uuid(), nullable=False),
        sa.Column("sale_item_id", sa.Uuid(), nullable=False), sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("product_name", sa.String(160), nullable=False), sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False), sa.Column("cost_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("return_to_stock", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("quantity > 0", name="ck_sale_return_items_quantity_positive"),
        sa.CheckConstraint("refund_amount >= 0", name="ck_sale_return_items_refund_nonnegative"),
        sa.ForeignKeyConstraint(["sale_return_id"], ["sale_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    for column in ("sale_return_id", "sale_item_id", "product_id"):
        op.create_index(f"ix_sale_return_items_{column}", "sale_return_items", [column])


def downgrade():
    op.drop_table("sale_return_items")
    op.drop_table("sale_returns")
