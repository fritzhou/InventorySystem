from decimal import Decimal

from sqlalchemy import select

from app.models import InventoryMovement, MovementType, Product, SaleReturn, SaleReturnItem
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
