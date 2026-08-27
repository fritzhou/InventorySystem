import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, func, inspect, select, text

from app.core.config import get_settings
from app.scripts.migrate_database import transfer_database

DESTRUCTIVE_ENABLED = (
    os.getenv("ALLOW_DESTRUCTIVE_POSTGRES_TESTS", "").lower() == "true"
    and bool(os.getenv("TEST_POSTGRES_URL"))
)
requires_disposable_postgres = pytest.mark.skipif(
    not DESTRUCTIVE_ENABLED,
    reason="requires TEST_POSTGRES_URL and ALLOW_DESTRUCTIVE_POSTGRES_TESTS=true",
)


def disposable_postgres_url() -> str:
    url = os.environ["TEST_POSTGRES_URL"]
    if url == os.getenv("DATABASE_URL"):
        pytest.fail("TEST_POSTGRES_URL must never equal DATABASE_URL")
    return url


def migrate(url: str, revision: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = url
        get_settings.cache_clear()
        getattr(command, "upgrade" if revision != "20260827_0007" else "downgrade")(Config("alembic.ini"), revision)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def reset_postgres(url: str) -> None:
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


@requires_disposable_postgres
def test_empty_postgresql_upgrade_downgrade_upgrade():
    url = disposable_postgres_url()
    reset_postgres(url)
    migrate(url, "head")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260827_0009"
            assert {"users", "user_sessions", "sales", "expenses", "audit_events"} <= set(inspect(connection).get_table_names())
        migrate(url, "20260827_0007")
        migrate(url, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260827_0009"
    finally:
        engine.dispose()


def seed_representative_source(source_url: str) -> dict[str, uuid.UUID]:
    engine = create_engine(source_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    ids = {name: uuid.uuid4() for name in ("user", "session", "category", "product", "sale", "sale_item", "return", "return_item", "movement", "supplier", "po", "po_item", "expense", "audit")}
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        expense_category_id = connection.scalar(select(metadata.tables["expense_categories"].c.id).limit(1))
        rows = {
            "users": dict(id=ids["user"], email="transfer@example.com", display_name="Transfer Admin", role="ADMIN", password_hash="scrypt$hash-only", is_active=True, must_change_password=False, last_login_at=now),
            "user_sessions": dict(id=ids["session"], user_id=ids["user"], token_hash="a" * 64, expires_at=now + timedelta(hours=1)),
            "categories": dict(id=ids["category"], name="Transfer Category", description="linked data"),
            "products": dict(id=ids["product"], name="Ten Cent Product", sku="TRANSFER-01", barcode=None, category_id=ids["category"], cost_price=Decimal("0.10"), selling_price=Decimal("0.10"), current_stock=5, minimum_stock=1, is_active=True),
            "sales": dict(id=ids["sale"], receipt_number="TRANSFER-SALE", subtotal=Decimal("0.10"), total=Decimal("0.10"), amount_tendered=Decimal("0.10"), change_due=Decimal("0.00"), payment_method="cash", processed_by_user_id=ids["user"]),
            "sale_items": dict(id=ids["sale_item"], sale_id=ids["sale"], product_id=ids["product"], product_name="Ten Cent Product", sku="TRANSFER-01", unit_price=Decimal("0.10"), cost_price=Decimal("0.10"), quantity=1, line_total=Decimal("0.10")),
            "sale_returns": dict(id=ids["return"], return_number="TRANSFER-RETURN", sale_id=ids["sale"], refund_total=Decimal("0.10"), reason="test", processed_by_user_id=ids["user"]),
            "sale_return_items": dict(id=ids["return_item"], sale_return_id=ids["return"], sale_item_id=ids["sale_item"], product_id=ids["product"], product_name="Ten Cent Product", sku="TRANSFER-01", unit_price=Decimal("0.10"), cost_price=Decimal("0.10"), quantity=1, refund_amount=Decimal("0.10"), return_to_stock=True),
            "inventory_movements": dict(id=ids["movement"], product_id=ids["product"], movement_type="SALE", quantity_change=-1, stock_before=6, stock_after=5, reference_type="SALE", reference_id=ids["sale"], note="transfer", actor_user_id=ids["user"]),
            "suppliers": dict(id=ids["supplier"], name="Transfer Supplier", contact_person=None, phone=None, email=None, address=None, notes=None, is_active=True),
            "purchase_orders": dict(id=ids["po"], po_number="TRANSFER-PO", supplier_id=ids["supplier"], status="ORDERED", order_date=date.today(), expected_date=None, notes=None, subtotal=Decimal("0.10")),
            "purchase_order_items": dict(id=ids["po_item"], purchase_order_id=ids["po"], product_id=ids["product"], product_name="Ten Cent Product", sku="TRANSFER-01", ordered_quantity=1, received_quantity=0, unit_cost=Decimal("0.10"), line_total=Decimal("0.10")),
            "expenses": dict(id=ids["expense"], expense_number="TRANSFER-EXPENSE", category_id=expense_category_id, category_name="Rent", description="Transfer expense", amount=Decimal("0.10"), expense_date=date.today(), notes=None, status="ACTIVE", voided_at=None, void_reason=None, created_by_user_id=ids["user"], updated_by_user_id=ids["user"], voided_by_user_id=None),
            "audit_events": dict(id=ids["audit"], actor_user_id=ids["user"], actor_email="transfer@example.com", actor_display_name="Transfer Admin", action="TRANSFER_TEST", entity_type="product", entity_id=str(ids["product"]), metadata={"safe": True}),
        }
        for table in metadata.sorted_tables:
            if table.name in rows:
                connection.execute(table.insert().values(**rows[table.name]))
    engine.dispose()
    return ids


@requires_disposable_postgres
def test_sqlite_to_postgresql_representative_transfer(tmp_path):
    target_url = disposable_postgres_url()
    source_url = f"sqlite:///{tmp_path / 'phase11-source.db'}"
    migrate(source_url, "head")
    ids = seed_representative_source(source_url)
    reset_postgres(target_url)
    migrate(target_url, "head")

    counts = transfer_database(source_url, target_url)
    target = create_engine(target_url)
    metadata = MetaData()
    metadata.reflect(bind=target)
    try:
        with target.connect() as connection:
            for name, source_count in counts.items():
                assert connection.scalar(select(func.count()).select_from(metadata.tables[name])) == source_count
            product = connection.execute(select(metadata.tables["products"]).where(metadata.tables["products"].c.id == ids["product"])).mappings().one()
            assert product["id"] == ids["product"]
            assert product["cost_price"] == Decimal("0.10")
            user = connection.execute(select(metadata.tables["users"]).where(metadata.tables["users"].c.id == ids["user"])).mappings().one()
            assert user["password_hash"] == "scrypt$hash-only"
            assert connection.scalar(select(func.count()).select_from(metadata.tables["user_sessions"])) == 0
            for name in {"categories", "sales", "sale_items", "sale_returns", "sale_return_items", "inventory_movements", "suppliers", "purchase_orders", "purchase_order_items", "expenses", "audit_events"}:
                assert connection.scalar(select(func.count()).select_from(metadata.tables[name])) > 0
    finally:
        target.dispose()
