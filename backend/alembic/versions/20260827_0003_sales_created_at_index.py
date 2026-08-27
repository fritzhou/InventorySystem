"""Index sales history by creation time.

Revision ID: 20260827_0003
"""
from typing import Sequence

from alembic import op

revision: str = "20260827_0003"
down_revision: str | None = "20260827_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_sales_created_at", "sales", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_sales_created_at", table_name="sales")
