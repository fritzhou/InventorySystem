"""operating expense categories and auditable expenses

Revision ID: 20260827_0008
Revises: 20260827_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_0008"
down_revision = "20260827_0007"
branch_labels = None
depends_on = None

DEFAULTS = ("Rent", "Utilities", "Salaries/Wages", "Transportation", "Supplies", "Maintenance", "Marketing", "Communication", "Miscellaneous")


def upgrade():
    categories = op.create_table("expense_categories",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True), sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index("uq_expense_categories_name_ci", "expense_categories", [sa.text("lower(name)")], unique=True)
    op.bulk_insert(categories, [{"id": __import__("uuid").uuid4(), "name": name, "description": None, "is_active": True} for name in DEFAULTS])
    op.create_table("expenses",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("expense_number", sa.String(40), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False), sa.Column("category_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=False), sa.Column("amount", sa.Numeric(12,2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False), sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "VOIDED", name="expensestatus"), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True), sa.Column("void_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("expense_number"))
    for column in ("expense_number", "category_id", "expense_date", "status"):
        op.create_index(f"ix_expenses_{column}", "expenses", [column], unique=column == "expense_number")
    op.create_index("ix_expenses_date_created", "expenses", ["expense_date", "created_at"])


def downgrade():
    op.drop_table("expenses")
    op.drop_table("expense_categories")
    # PostgreSQL ENUM types are independent schema objects; without cleanup a
    # downgrade followed by an upgrade fails because the type already exists.
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="expensestatus").drop(op.get_bind(), checkfirst=True)
