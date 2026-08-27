import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Category, Product, Sale, SaleItem


def make_product(db, name="Coke", sku="COKE", price="25.00", stock=5, active=True):
    category = db.scalar(select(Category).where(Category.name == "Drinks"))
    if category is None:
        category = Category(name="Drinks")
        db.add(category)
        db.flush()
    product = Product(
        name=name, sku=sku, barcode=f"480{uuid.uuid4().int % 10**10:010d}", category_id=category.id,
        cost_price=Decimal("10.00"), selling_price=Decimal(price), current_stock=stock,
        minimum_stock=0, is_active=active,
    )
    db.add(product)
    db.commit()
    return product


def checkout(client, items, cash="100.00"):
    return client.post("/api/sales", json={"items": items, "amount_tendered": cash})


def test_successful_sale_deducts_stock_and_uses_database_price(client, db):
    product = make_product(db)
    response = checkout(client, [{"product_id": str(product.id), "quantity": 2, "unit_price": "0.01"}])
    assert response.status_code == 201
    body = response.json()
    assert body["receipt_number"].startswith("SF-")
    assert body["total"] == "50.00"
    assert body["change_due"] == "50.00"
    item = body["items"][0]
    assert (item["product_name"], item["sku"], item["unit_price"], item["quantity"], item["line_total"]) == (
        "Coke", "COKE", "25.00", 2, "50.00"
    )
    db.expire_all()
    assert db.get(Product, product.id).current_stock == 3


def test_multiple_products_and_duplicate_lines_are_aggregated(client, db):
    coke = make_product(db)
    water = make_product(db, "Water", "WATER", "20.00", 4)
    response = checkout(client, [
        {"product_id": str(coke.id), "quantity": 1},
        {"product_id": str(coke.id), "quantity": 1},
        {"product_id": str(water.id), "quantity": 1},
    ])
    assert response.status_code == 201
    assert response.json()["total"] == "70.00"
    assert sorted(item["quantity"] for item in response.json()["items"]) == [1, 2]


def test_insufficient_stock_rolls_back_entire_checkout(client, db):
    coke = make_product(db, stock=1)
    water = make_product(db, "Water", "WATER", "20.00", 4)
    response = checkout(client, [
        {"product_id": str(water.id), "quantity": 1},
        {"product_id": str(coke.id), "quantity": 2},
    ])
    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient stock for Coke. Available: 1"
    db.expire_all()
    assert db.get(Product, water.id).current_stock == 4
    assert db.scalar(select(func.count()).select_from(Sale)) == 0
    assert db.scalar(select(func.count()).select_from(SaleItem)) == 0


def test_inactive_product_is_rejected(client, db):
    product = make_product(db, active=False)
    response = checkout(client, [{"product_id": str(product.id), "quantity": 1}])
    assert response.status_code == 409
    assert "Product is inactive" in response.json()["detail"]


def test_nonexistent_product_is_rejected(client):
    response = checkout(client, [{"product_id": str(uuid.uuid4()), "quantity": 1}])
    assert response.status_code == 404
    assert response.json()["detail"] == "Product no longer exists"


def test_cash_below_total_does_not_change_stock(client, db):
    product = make_product(db)
    response = checkout(client, [{"product_id": str(product.id), "quantity": 1}], "24.99")
    assert response.status_code == 422
    assert response.json()["detail"] == "Amount tendered is less than total"
    db.expire_all()
    assert db.get(Product, product.id).current_stock == 5
    assert db.scalar(select(func.count()).select_from(Sale)) == 0


def test_invalid_quantity_is_rejected_by_schema(client, db):
    product = make_product(db)
    response = checkout(client, [{"product_id": str(product.id), "quantity": 0}])
    assert response.status_code == 422
    db.expire_all()
    assert db.get(Product, product.id).current_stock == 5
