from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import MetaData, create_engine, func, select, text

from app.scripts.migrate_database import HEAD, transfer
from app.scripts.postgres_safety import destructive_test_database_url
from tests.test_postgres_integration import alembic_config, reset


def _url_or_skip() -> str:
    try:
        return destructive_test_database_url()
    except RuntimeError as exc:
        pytest.skip(str(exc))


def _upgrade(url: str) -> None:
    command.upgrade(alembic_config(url), "head")


def _make_source(path: Path) -> tuple[str, dict[str, object]]:
    url = f"sqlite:///{path}"
    _upgrade(url)
    engine = create_engine(url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    ids = {name: uuid4() for name in ("user", "session", "category", "product", "supplier", "po", "po_item",
                                      "sale", "sale_item", "return", "return_item", "movement", "expense", "audit")}
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        expense_category = connection.execute(select(metadata.tables["expense_categories"])).mappings().first()
        connection.execute(metadata.tables["users"].insert(), {"id": ids["user"], "email": "transfer@example.com",
            "display_name": "Transfer Admin", "role": "ADMIN", "password_hash": "preserved-password-hash",
            "is_active": True, "must_change_password": False, "created_at": now, "updated_at": now})
        connection.execute(metadata.tables["user_sessions"].insert(), {"id": ids["session"], "user_id": ids["user"],
            "token_hash": "a" * 64, "created_at": now, "expires_at": now + timedelta(hours=1)})
        connection.execute(metadata.tables["categories"].insert(), {"id": ids["category"], "name": "Transfer Category",
            "description": "linked", "created_at": now})
        connection.execute(metadata.tables["products"].insert(), {"id": ids["product"], "name": "Exact Product", "sku": "XFER-1",
            "category_id": ids["category"], "cost_price": Decimal("0.10"), "selling_price": Decimal("999999.99"),
            "current_stock": 4, "minimum_stock": 1, "is_active": True, "created_at": now, "updated_at": now})
        connection.execute(metadata.tables["suppliers"].insert(), {"id": ids["supplier"], "name": "Transfer Supplier",
            "is_active": True, "created_at": now, "updated_at": now})
        connection.execute(metadata.tables["purchase_orders"].insert(), {"id": ids["po"], "po_number": "PO-XFER",
            "supplier_id": ids["supplier"], "status": "RECEIVED", "order_date": date.today(), "subtotal": Decimal("0.10"),
            "created_at": now, "updated_at": now})
        connection.execute(metadata.tables["purchase_order_items"].insert(), {"id": ids["po_item"], "purchase_order_id": ids["po"],
            "product_id": ids["product"], "product_name": "Exact Product", "sku": "XFER-1", "ordered_quantity": 1,
            "received_quantity": 1, "unit_cost": Decimal("0.10"), "line_total": Decimal("0.10")})
        connection.execute(metadata.tables["sales"].insert(), {"id": ids["sale"], "receipt_number": "R-XFER",
            "subtotal": Decimal("0.10"), "total": Decimal("0.10"), "amount_tendered": Decimal("0.10"),
            "change_due": Decimal("0.00"), "payment_method": "CASH", "created_at": now,
            "processed_by_user_id": ids["user"]})
        connection.execute(metadata.tables["sale_items"].insert(), {"id": ids["sale_item"], "sale_id": ids["sale"],
            "product_id": ids["product"], "product_name": "Exact Product", "sku": "XFER-1", "unit_price": Decimal("0.10"),
            "cost_price": Decimal("0.10"), "quantity": 1, "line_total": Decimal("0.10")})
        connection.execute(metadata.tables["sale_returns"].insert(), {"id": ids["return"], "return_number": "RET-XFER",
            "sale_id": ids["sale"], "refund_total": Decimal("0.10"), "created_at": now,
            "processed_by_user_id": ids["user"]})
        connection.execute(metadata.tables["sale_return_items"].insert(), {"id": ids["return_item"], "sale_return_id": ids["return"],
            "sale_item_id": ids["sale_item"], "product_id": ids["product"], "product_name": "Exact Product", "sku": "XFER-1",
            "unit_price": Decimal("0.10"), "cost_price": Decimal("0.10"), "quantity": 1,
            "refund_amount": Decimal("0.10"), "return_to_stock": True})
        connection.execute(metadata.tables["inventory_movements"].insert(), {"id": ids["movement"], "product_id": ids["product"],
            "movement_type": "SALE", "quantity_change": -1, "stock_before": 5, "stock_after": 4, "reference_type": "SALE",
            "reference_id": ids["sale"], "created_at": now, "actor_user_id": ids["user"]})
        connection.execute(metadata.tables["expenses"].insert(), {"id": ids["expense"], "expense_number": "EXP-XFER",
            "category_id": expense_category["id"], "category_name": expense_category["name"], "description": "Exact expense",
            "amount": Decimal("0.10"), "expense_date": date.today(), "status": "ACTIVE", "created_at": now, "updated_at": now,
            "created_by_user_id": ids["user"]})
        connection.execute(metadata.tables["audit_events"].insert(), {"id": ids["audit"], "actor_user_id": ids["user"],
            "actor_email": "transfer@example.com", "actor_display_name": "Transfer Admin", "action": "TRANSFER_TEST",
            "entity_type": "product", "entity_id": str(ids["product"]), "metadata": {"safe": True}, "created_at": now})
    engine.dispose()
    return url, ids


def test_real_sqlite_to_postgres_transfer(tmp_path: Path):
    target_url = _url_or_skip()
    source_url, ids = _make_source(tmp_path / "source.db")
    reset(target_url)
    _upgrade(target_url)
    counts = transfer(source_url, target_url)
    engine = create_engine(target_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    with engine.connect() as connection:
        assert connection.dialect.name == "postgresql"
        product = connection.execute(select(metadata.tables["products"])).mappings().one()
        user = connection.execute(select(metadata.tables["users"])).mappings().one()
        assert product["id"] == ids["product"] and product["category_id"] == ids["category"]
        assert product["cost_price"] == Decimal("0.10") and product["selling_price"] == Decimal("999999.99")
        assert user["password_hash"] == "preserved-password-hash"
        assert connection.scalar(select(func.count()).select_from(metadata.tables["user_sessions"])) == 0
        assert connection.scalar(select(metadata.tables["alembic_version"].c.version_num)) == HEAD
        for table in ("categories", "suppliers", "purchase_orders", "purchase_order_items", "sales", "sale_items",
                      "sale_returns", "sale_return_items", "inventory_movements", "expenses", "audit_events"):
            assert counts[table] == 1
            assert connection.scalar(select(func.count()).select_from(metadata.tables[table])) == 1
    engine.dispose()


@pytest.mark.parametrize("mutation", [
    "UPDATE expense_categories SET description = 'customized' WHERE name = 'Rent'",
    "UPDATE expense_categories SET is_active = false WHERE name = 'Rent'",
    "UPDATE expense_categories SET name = 'Renamed' WHERE name = 'Rent'",
    "DELETE FROM expense_categories WHERE name = 'Rent'",
])
def test_transfer_rejects_modified_migration_seed_categories(tmp_path: Path, mutation: str):
    target_url = _url_or_skip()
    source_url, _ = _make_source(tmp_path / "source.db")
    reset(target_url)
    _upgrade(target_url)
    engine = create_engine(target_url)
    with engine.begin() as connection:
        connection.execute(text(mutation))
    with pytest.raises(RuntimeError, match="not untouched"):
        transfer(source_url, target_url, dry_run=True)
    engine.dispose()
