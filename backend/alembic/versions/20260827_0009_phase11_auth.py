"""Phase 11 authentication, actors and immutable audit events."""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260827_0009"
down_revision: str | None = "20260827_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    with op.batch_alter_table("users") as batch:
        batch.alter_column("full_name", new_column_name="display_name", existing_type=sa.String(120))
        batch.add_column(sa.Column("password_hash", sa.String(512), nullable=True))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    if dialect == "postgresql":
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(20) USING role::text")
    else:
        with op.batch_alter_table("users") as batch:
            batch.alter_column("role", existing_type=sa.Enum("ADMIN", "CASHIER", name="user_role"), type_=sa.String(20), existing_nullable=False)
    # Existing installations should contain no usable accounts because authentication did not exist.
    # NULL is retained only long enough for portable migration; bootstrap refuses duplicate users.
    op.execute(sa.update(sa.table("users", sa.column("is_active"), sa.column("password_hash")))
               .where(sa.column("password_hash").is_(None)).values(is_active=False))
    op.create_index("ux_users_email_lower", "users", [sa.text("lower(email)")], unique=True)
    op.create_table("user_sessions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_sessions_user_id_users", ondelete="CASCADE"))
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_table("audit_events", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("actor_user_id", sa.Uuid()), sa.Column("actor_email", sa.String(320)), sa.Column("actor_display_name", sa.String(120)), sa.Column("action", sa.String(80), nullable=False), sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(80)), sa.Column("metadata", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_audit_events_actor_user_id_users", ondelete="SET NULL"))
    for table, columns in {"sales":["processed_by_user_id"], "sale_returns":["processed_by_user_id"], "inventory_movements":["actor_user_id"], "expenses":["created_by_user_id","updated_by_user_id","voided_by_user_id"]}.items():
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.add_column(sa.Column(column, sa.Uuid(), nullable=True))
                batch.create_foreign_key(f"fk_{table}_{column}_users", "users", [column], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    # The old enum cannot represent MANAGER. A downgraded installation maps
    # those accounts to CASHIER before the Phase 11 activation field is removed.
    users = sa.table("users", sa.column("role", sa.String()), sa.column("is_active", sa.Boolean()))
    op.execute(sa.update(users).where(users.c.role == "MANAGER").values(role="CASHIER", is_active=False))
    for table, columns in {"expenses":["voided_by_user_id","updated_by_user_id","created_by_user_id"], "inventory_movements":["actor_user_id"], "sale_returns":["processed_by_user_id"], "sales":["processed_by_user_id"]}.items():
        with op.batch_alter_table(table) as batch:
            for column in columns: batch.drop_column(column)
    op.drop_table("audit_events"); op.drop_table("user_sessions"); op.drop_index("ux_users_email_lower", table_name="users")
    with op.batch_alter_table("users") as batch:
        for column in ["last_login_at", "updated_at", "must_change_password", "is_active", "password_hash"]: batch.drop_column(column)
        batch.alter_column("display_name", new_column_name="full_name", existing_type=sa.String(120))
    if dialect == "postgresql":
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::text::user_role")
    else:
        with op.batch_alter_table("users") as batch:
            batch.alter_column("role", existing_type=sa.String(20), type_=sa.Enum("ADMIN", "CASHIER", name="user_role"), existing_nullable=False)
