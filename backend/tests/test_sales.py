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


def test_list_sales_is_newest_first_and_reports_item_counts(client, db):
    from datetime import datetime, timezone
    first = checkout(client, [{"product_id": str(make_product(db).id), "quantity": 1}]).json()
    second = checkout(client, [{"product_id": str(make_product(db, "Water", "WATER").id), "quantity": 2}]).json()
    db.get(Sale, uuid.UUID(first["id"])).created_at = datetime(2026, 8, 26, tzinfo=timezone.utc)
    db.get(Sale, uuid.UUID(second["id"])).created_at = datetime(2026, 8, 27, tzinfo=timezone.utc)
    db.commit()
    body = client.get("/api/sales").json()
    assert [item["id"] for item in body["items"]] == [second["id"], first["id"]]
    assert body["items"][0]["item_count"] == 2
    assert body | {"items": []} == {"items": [], "page": 1, "page_size": 20, "total_items": 2, "total_pages": 1}


def test_list_sales_search_is_case_insensitive(client, db):
    sale = checkout(client, [{"product_id": str(make_product(db).id), "quantity": 1}]).json()
    suffix = sale["receipt_number"][3:8].lower()
    body = client.get("/api/sales", params={"search": suffix}).json()
    assert [item["id"] for item in body["items"]] == [sale["id"]]
    assert client.get("/api/sales", params={"search": "does-not-exist"}).json()["items"] == []


def test_list_sales_paginates(client, db):
    from datetime import datetime, timedelta, timezone
    product = make_product(db, stock=5)
    ids = [checkout(client, [{"product_id": str(product.id), "quantity": 1}]).json()["id"] for _ in range(3)]
    for offset, sale_id in enumerate(ids):
        db.get(Sale, uuid.UUID(sale_id)).created_at = datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(days=offset)
    db.commit()
    body = client.get("/api/sales", params={"page": 2, "page_size": 2}).json()
    assert body["page"] == 2 and body["total_items"] == 3 and body["total_pages"] == 2
    assert len(body["items"]) == 1 and body["items"][0]["id"] == ids[0]


def test_list_sales_filters_inclusive_dates_and_rejects_invalid_range(client, db):
    from datetime import datetime, timezone
    product = make_product(db, stock=3)
    sales = [checkout(client, [{"product_id": str(product.id), "quantity": 1}]).json() for _ in range(2)]
    db.get(Sale, uuid.UUID(sales[0]["id"])).created_at = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    db.get(Sale, uuid.UUID(sales[1]["id"])).created_at = datetime(2026, 8, 27, 23, 59, tzinfo=timezone.utc)
    db.commit()
    assert client.get("/api/sales", params={"start_date": "2026-08-27"}).json()["total_items"] == 1
    assert client.get("/api/sales", params={"end_date": "2026-08-01"}).json()["total_items"] == 1
    invalid = client.get("/api/sales", params={"start_date": "2026-08-28", "end_date": "2026-08-01"})
    assert invalid.status_code == 422 and invalid.json()["detail"] == "From date cannot be after To date"


def test_sale_detail_uses_historical_snapshots_after_product_edit(client, db):
    product = make_product(db, name="Original", price="25.00")
    created = checkout(client, [{"product_id": str(product.id), "quantity": 1}]).json()
    product.name = "Renamed"
    product.selling_price = Decimal("99.00")
    db.commit()
    body = client.get(f"/api/sales/{created['id']}").json()
    assert body["items"][0]["product_name"] == "Original"
    assert body["items"][0]["unit_price"] == "25.00"


def test_nonexistent_sale_detail_returns_safe_404(client):
    response = client.get(f"/api/sales/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Receipt not found"}
