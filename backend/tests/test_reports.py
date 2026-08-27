from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
import uuid

from app.models import Category, Product, Sale, SaleItem, SaleReturn
from test_sales import checkout


def product(db, name, sku, stock, minimum, active=True):
    category = db.scalar(select(Category).where(Category.name == "Report"))
    if not category:
        category = Category(name="Report"); db.add(category); db.flush()
    item = Product(name=name, sku=sku, category_id=category.id, cost_price=Decimal("10"), selling_price=Decimal("25"), current_stock=stock, minimum_stock=minimum, is_active=active)
    db.add(item); db.commit(); return item


def test_empty_dashboard_and_stock_metrics(client, db):
    product(db, "Low", "LOW", 2, 3); product(db, "Out", "OUT", 0, 3); product(db, "Hidden", "HIDE", 0, 3, False)
    body = client.get("/api/reports/dashboard").json()
    assert body["sales_total"] == "0.00" and body["transaction_count"] == 0 and body["items_sold"] == 0
    assert body["gross_profit"] == "0.00" and body["profit_complete"] is True and body["average_transaction_value"] == "0.00"
    assert body["low_stock_count"] == 1 and body["out_of_stock_count"] == 1 and body["total_active_products"] == 2


def test_profit_uses_snapshot_and_missing_cost_is_honest(client, db):
    item = product(db, "Coke", "COKE", 20, 2)
    client.post("/api/sales", json={"items": [{"product_id": str(item.id), "quantity": 2}], "amount_tendered": "100"})
    db.get(Product, item.id).cost_price = Decimal("24")
    old = Sale(receipt_number="OLD", subtotal=25, total=25, amount_tendered=25, change_due=0, payment_method="cash", created_at=datetime.now(timezone.utc)); db.add(old); db.flush()
    db.add(SaleItem(sale_id=old.id, product_id=item.id, product_name="Old Coke", sku="OLD-COKE", unit_price=25, cost_price=None, quantity=1, line_total=25)); db.commit()
    body = client.get("/api/reports/dashboard").json()
    assert body["sales_total"] == "75.00" and body["transaction_count"] == 2 and body["items_sold"] == 3
    assert body["gross_profit"] == "30.00" and body["profit_complete"] is False and body["average_transaction_value"] == "37.50"
    assert [row["product_name"] for row in client.get("/api/reports/top-products").json()] == ["Coke", "Old Coke"]


def test_custom_range_validation_and_continuous_ordered_trend(client):
    assert client.get("/api/reports/summary", params={"start_date": "2026-08-28", "end_date": "2026-08-27"}).status_code == 422
    trend = client.get("/api/reports/sales-trend", params={"start_date": "2026-08-25", "end_date": "2026-08-27"}).json()
    assert [point["date"] for point in trend] == ["2026-08-25", "2026-08-26", "2026-08-27"]


def test_returns_adjust_dashboard_profit_top_products_and_return_date_trend(client, db):
    item = product(db, "Original Coke", "OLD-COKE", 5, 0)
    first = checkout(client, [{"product_id": str(item.id), "quantity": 1}]).json()
    item.name = "Renamed Coke"; item.sku = "NEW-COKE"; db.commit()
    second = checkout(client, [{"product_id": str(item.id), "quantity": 1}]).json()
    original_sale_item = dict(first["items"][0])
    returned = client.post(f"/api/sales/{first['id']}/returns", json={"items": [{
        "sale_item_id": first["items"][0]["id"], "quantity": 1, "return_to_stock": False,
    }]}).json()
    sale_day = datetime(2026, 8, 25, 4, 0, tzinfo=timezone.utc)
    return_day = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
    db.get(Sale, uuid.UUID(first["id"])).created_at = sale_day
    db.get(Sale, uuid.UUID(second["id"])).created_at = sale_day
    db.get(SaleReturn, uuid.UUID(returned["id"])).created_at = return_day
    db.commit()

    dashboard = client.get("/api/reports/dashboard", params={"start_date": "2026-08-25", "end_date": "2026-08-26"}).json()
    assert dashboard["sales_total"] == "25.00"
    assert dashboard["items_sold"] == 1
    assert dashboard["gross_profit"] == "15.00"
    assert dashboard["profit_complete"] is True

    top = client.get("/api/reports/top-products", params={"start_date": "2026-08-25", "end_date": "2026-08-26"}).json()
    by_snapshot = {(row["product_name"], row["sku"]): row for row in top}
    assert by_snapshot[("Original Coke", "OLD-COKE")]["quantity_sold"] == 0
    assert by_snapshot[("Original Coke", "OLD-COKE")]["revenue"] == "0.00"
    assert by_snapshot[("Renamed Coke", "NEW-COKE")]["quantity_sold"] == 1
    assert by_snapshot[("Renamed Coke", "NEW-COKE")]["revenue"] == "25.00"

    trend = client.get("/api/reports/sales-trend", params={"start_date": "2026-08-25", "end_date": "2026-08-26"}).json()
    assert [(point["date"], point["sales"], point["items_sold"]) for point in trend] == [
        ("2026-08-25", "50.00", 2), ("2026-08-26", "-25.00", -1),
    ]
    # Return reporting never rewrites the original financial snapshots.
    unchanged = db.get(SaleItem, uuid.UUID(first["items"][0]["id"]))
    assert unchanged.product_name == original_sale_item["product_name"]
    assert unchanged.sku == original_sale_item["sku"]
    assert unchanged.unit_price == Decimal(original_sale_item["unit_price"])
    assert db.get(Sale, uuid.UUID(first["id"])).total == Decimal(first["total"])


def test_return_with_legacy_null_cost_keeps_profit_incomplete(client, db):
    item = product(db, "Legacy", "LEGACY", 2, 0)
    sale = checkout(client, [{"product_id": str(item.id), "quantity": 1}]).json()
    line = db.get(SaleItem, uuid.UUID(sale["items"][0]["id"])); line.cost_price = None; db.commit()
    returned = client.post(f"/api/sales/{sale['id']}/returns", json={"items": [{
        "sale_item_id": sale["items"][0]["id"], "quantity": 1, "return_to_stock": False,
    }]}).json()
    when = datetime(2026, 8, 27, 4, 0, tzinfo=timezone.utc)
    db.get(Sale, uuid.UUID(sale["id"])).created_at = when
    db.get(SaleReturn, uuid.UUID(returned["id"])).created_at = when
    db.commit()
    summary = client.get("/api/reports/summary", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()
    assert summary["sales_total"] == "0.00" and summary["items_sold"] == 0
    assert summary["gross_profit"] == "0.00" and summary["profit_complete"] is False
