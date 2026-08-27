import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models import InventoryMovement, MovementType, Product, SaleItem, SaleReturn, SaleReturnItem
from test_sales import checkout, make_product


def create_sale(client, db, *, quantity=3, price="25.00", stock=10):
    product = make_product(db, price=price, stock=stock)
    sale = checkout(client, [{"product_id": str(product.id), "quantity": quantity}], "500.00").json()
    return product, sale


def return_item(client, sale, quantity, restock=True):
    return client.post(f"/api/sales/{sale['id']}/returns", json={"reason": "Customer changed mind", "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": quantity, "return_to_stock": restock}]})


def test_partial_multiple_and_full_returns_preserve_sale_snapshots(client, db):
    product, sale = create_sale(client, db, quantity=5)
    original = dict(sale)
    assert return_item(client, sale, 2, False).json()["refund_total"] == "50.00"
    assert return_item(client, sale, 1, False).status_code == 201
    detail = client.get(f"/api/sales/{sale['id']}").json()
    assert detail["items"][0]["returned_quantity"] == 3
    assert detail["items"][0]["returnable_quantity"] == 2
    assert return_item(client, sale, 2, False).status_code == 201
    assert return_item(client, sale, 1, False).status_code == 409
    db.expire_all()
    assert db.get(Product, product.id).current_stock == 5
    assert detail["total"] == original["total"] and detail["items"][0]["unit_price"] == original["items"][0]["unit_price"]


def test_refund_uses_historical_price_and_cost_not_current_product(client, db):
    product, sale = create_sale(client, db)
    product.selling_price = Decimal("99.00"); product.cost_price = Decimal("88.00"); db.commit()
    returned = return_item(client, sale, 1, False).json()
    assert returned["refund_total"] == "25.00"
    assert returned["items"][0]["unit_price"] == "25.00"
    assert returned["items"][0]["cost_price"] == "10.00"


def test_restock_creates_auditable_return_movement(client, db):
    product, sale = create_sale(client, db)
    returned = return_item(client, sale, 1, True).json(); db.expire_all()
    assert db.get(Product, product.id).current_stock == 8
    movement = db.scalar(select(InventoryMovement).where(InventoryMovement.reference_id == returned["id"]))
    assert movement.movement_type == MovementType.RETURN
    assert (movement.quantity_change, movement.stock_before, movement.stock_after) == (1, 7, 8)
    assert movement.reference_type == "SALE_RETURN" and movement.note == returned["return_number"]


def test_inactive_product_allows_financial_return_but_rejects_restock_atomically(client, db):
    product, sale = create_sale(client, db)
    product.is_active = False; db.commit()
    rejected = return_item(client, sale, 1, True)
    assert rejected.status_code == 409 and "inactive" in rejected.json()["detail"]
    assert db.scalar(select(SaleReturn)) is None and db.scalar(select(SaleReturnItem)) is None
    assert return_item(client, sale, 1, False).status_code == 201


def test_duplicate_and_over_return_are_rejected(client, db):
    _, sale = create_sale(client, db, quantity=1)
    item = {"sale_item_id": sale["items"][0]["id"], "quantity": 1, "return_to_stock": False}
    duplicate = client.post(f"/api/sales/{sale['id']}/returns", json={"items": [item, item]})
    assert duplicate.status_code == 422
    assert return_item(client, sale, 1, False).status_code == 201
    assert return_item(client, sale, 1, False).status_code == 409


def test_return_restock_recalculates_weighted_cost_and_future_sale_uses_it(client, db):
    product, sale = create_sale(client, db, quantity=2, stock=4)
    # The sold units retain their 10.00 cost while current inventory is repriced.
    product.cost_price = Decimal("20.00"); db.commit()
    assert return_item(client, sale, 1, True).status_code == 201
    db.expire_all()
    # Before return: 2 @ 20.00; returned: 1 @ 10.00 => 16.67.
    assert db.get(Product, product.id).cost_price == Decimal("16.67")
    future = checkout(client, [{"product_id": str(product.id), "quantity": 1}], "100.00").json()
    assert db.get(SaleItem, uuid.UUID(future["items"][0]["id"])).cost_price == Decimal("16.67")


def test_legacy_null_cost_restock_preserves_current_average_cost(client, db):
    product, sale = create_sale(client, db, quantity=1)
    db.get(SaleItem, uuid.UUID(sale["items"][0]["id"])).cost_price = None
    product.cost_price = Decimal("18.25"); db.commit()
    assert return_item(client, sale, 1, True).status_code == 201
    db.expire_all()
    assert db.get(Product, product.id).cost_price == Decimal("18.25")


def test_return_history_filters_on_manila_calendar_date(client, db):
    _, sale = create_sale(client, db, quantity=1)
    returned = return_item(client, sale, 1, False).json()
    # 16:30 UTC is 00:30 on the following Asia/Manila calendar date.
    db.get(SaleReturn, uuid.UUID(returned["id"])).created_at = datetime(2026, 8, 26, 16, 30, tzinfo=timezone.utc)
    db.commit()
    on_manila_date = client.get("/api/returns", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()
    prior_date = client.get("/api/returns", params={"start_date": "2026-08-26", "end_date": "2026-08-26"}).json()
    assert [item["id"] for item in on_manila_date["items"]] == [returned["id"]]
    assert prior_date["items"] == []
