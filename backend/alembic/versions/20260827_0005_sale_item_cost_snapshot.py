"""Add sale-time cost price snapshots for profit reporting.

Revision ID: 20260827_0005
"""
from typing import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0005"
down_revision: str | None = "20260827_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable intentionally: pre-Phase-7 sales have no trustworthy cost snapshot.
    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.add_column(sa.Column("cost_price", sa.Numeric(12, 2), nullable=True))
        batch_op.create_check_constraint("ck_sale_items_cost_price_nonnegative", "cost_price >= 0")


def downgrade() -> None:
    with op.batch_alter_table("sale_items") as batch_op:
        batch_op.drop_constraint("ck_sale_items_cost_price_nonnegative", type_="check")
        batch_op.drop_column("cost_price")
