from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from app.models import Category, Product, Sale, SaleItem


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
