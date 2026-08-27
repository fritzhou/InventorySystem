"""Add inventory movement audit trail.

Revision ID: 20260827_0004
"""
from typing import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0004"
down_revision: str | None = "20260827_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("inventory_movements",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.Enum("RESTOCK", "SALE", "DAMAGE", "CORRECTION", name="movementtype", native_enum=False), nullable=False),
        sa.Column("quantity_change", sa.Integer(), nullable=False), sa.Column("stock_before", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False), sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True), sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("stock_before >= 0", name="ck_inventory_movements_stock_before_nonnegative"),
        sa.CheckConstraint("stock_after >= 0", name="ck_inventory_movements_stock_after_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    for column in ("product_id", "created_at", "reference_id"):
        op.create_index(f"ix_inventory_movements_{column}", "inventory_movements", [column])


def downgrade() -> None:
    op.drop_table("inventory_movements")
