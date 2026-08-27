import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Category, InventoryMovement, MovementType, Product


def product(db, stock=10, active=True, name="Water", sku=None):
    category = db.scalar(select(Category).where(Category.name == "Inventory"))
    if not category:
        category = Category(name="Inventory"); db.add(category); db.flush()
    item = Product(name=name, sku=sku or uuid.uuid4().hex, category_id=category.id, cost_price=Decimal("1"),
                   selling_price=Decimal("2"), current_stock=stock, minimum_stock=0, is_active=active)
    db.add(item); db.commit(); return item


def adjust(client, item, payload):
    return client.post(f"/api/products/{item.id}/stock-adjustments", json=payload)


def test_restock_damage_and_corrections_create_snapshots(client, db):
    item = product(db)
    restock = adjust(client, item, {"type": "RESTOCK", "quantity": 5, "note": "Delivery"})
    assert restock.status_code == 201 and (restock.json()["quantity_change"], restock.json()["stock_before"], restock.json()["stock_after"]) == (5, 10, 15)
    damage = adjust(client, item, {"type": "DAMAGE", "quantity": 2})
    assert (damage.json()["quantity_change"], damage.json()["stock_after"]) == (-2, 13)
    upward = adjust(client, item, {"type": "CORRECTION", "actual_stock": 20})
    assert upward.json()["quantity_change"] == 7
    downward = adjust(client, item, {"type": "CORRECTION", "actual_stock": 8})
    assert downward.json()["quantity_change"] == -12
    assert db.scalar(select(func.count()).select_from(InventoryMovement)) == 4


def test_invalid_adjustments_are_safe(client, db):
    item = product(db, stock=3)
    assert adjust(client, item, {"type": "DAMAGE", "quantity": 5}).status_code == 409
    assert adjust(client, item, {"type": "RESTOCK", "quantity": 0}).status_code == 422
    assert adjust(client, item, {"type": "SALE", "quantity": 1}).status_code == 422
    assert client.post(f"/api/products/{uuid.uuid4()}/stock-adjustments", json={"type": "RESTOCK", "quantity": 1}).status_code == 404
    db.expire_all()
    assert db.get(Product, item.id).current_stock == 3
    assert db.scalar(select(func.count()).select_from(InventoryMovement)) == 0


def test_sale_movement_and_failed_checkout_atomicity(client, db):
    item = product(db, stock=4)
    sold = client.post("/api/sales", json={"items": [{"product_id": str(item.id), "quantity": 2}], "amount_tendered": "10"})
    movement = db.scalar(select(InventoryMovement))
    assert sold.status_code == 201
    assert (movement.movement_type, movement.quantity_change, movement.stock_before, movement.stock_after) == (MovementType.SALE, -2, 4, 2)
    assert str(movement.reference_id) == sold.json()["id"]
    failed = client.post("/api/sales", json={"items": [{"product_id": str(item.id), "quantity": 3}], "amount_tendered": "10"})
    assert failed.status_code == 409
    assert db.scalar(select(func.count()).select_from(InventoryMovement)) == 1


def test_history_filters_pagination_dates_and_inactive_products(client, db):
    first = product(db, name="Water", sku="WATER")
    second = product(db, name="Cola", sku="COLA")
    a = adjust(client, first, {"type": "RESTOCK", "quantity": 1}).json()
    b = adjust(client, second, {"type": "DAMAGE", "quantity": 1}).json()
    db.get(InventoryMovement, uuid.UUID(a["id"])).created_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    db.get(InventoryMovement, uuid.UUID(b["id"])).created_at = datetime(2026, 8, 27, tzinfo=timezone.utc)
    first.is_active = False; db.commit()
    body = client.get("/api/inventory/movements").json()
    assert [row["id"] for row in body["items"]] == [b["id"], a["id"]]
    assert client.get("/api/inventory/movements", params={"product_id": str(first.id)}).json()["items"][0]["product"]["is_active"] is False
    assert client.get("/api/inventory/movements", params={"movement_type": "DAMAGE"}).json()["total_items"] == 1
    assert client.get("/api/inventory/movements", params={"start_date": "2026-08-27"}).json()["total_items"] == 1
    page = client.get("/api/inventory/movements", params={"page": 2, "page_size": 1}).json()
    assert page["total_pages"] == 2 and len(page["items"]) == 1
