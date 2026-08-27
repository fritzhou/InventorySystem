from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import uuid

from app.models import Expense, Sale, SaleItem, SaleReturn, SaleReturnItem
from test_purchasing import draft, order, receive
from test_reports import product


def category(client, name="Utilities"):
    response = client.post("/api/expense-categories", json={"name": name})
    assert response.status_code == 201
    return response.json()


def expense(client, category_id, **overrides):
    payload = {"category_id": category_id, "description": "Electricity bill", "amount": "1250.00",
               "expense_date": "2026-08-27", "notes": "Store electricity"}
    payload.update(overrides)
    response = client.post("/api/expenses", json=payload)
    assert response.status_code == 201
    return response.json()


def test_default_categories_are_migrated():
    migration = (Path(__file__).parents[1] / "alembic/versions/20260827_0008_operating_expenses.py").read_text()
    for name in ("Rent", "Utilities", "Salaries/Wages", "Transportation", "Supplies",
                 "Maintenance", "Marketing", "Communication", "Miscellaneous"):
        assert f'"{name}"' in migration


def test_category_create_edit_duplicate_and_deactivate(client):
    item = category(client)
    duplicate = client.post("/api/expense-categories", json={"name": "uTiLiTiEs"})
    assert duplicate.status_code == 409
    edited = client.patch(f"/api/expense-categories/{item['id']}", json={"name": "Power", "description": None})
    assert edited.status_code == 200 and edited.json()["name"] == "Power"
    assert client.patch(f"/api/expense-categories/{item['id']}", json={"name": None}).status_code == 422
    assert client.delete(f"/api/expense-categories/{item['id']}").json()["is_active"] is False
    assert client.post("/api/expenses", json={"category_id": item["id"], "description": "Bill",
        "amount": "1.00", "expense_date": "2026-08-27"}).status_code == 422


def test_create_decimal_validation_edit_and_explicit_nulls(client, db):
    cat = category(client)
    item = expense(client, cat["id"])
    stored = db.get(Expense, uuid.UUID(item["id"]))
    assert stored.amount == Decimal("1250.00") and item["expense_number"].startswith("EXP-")
    for amount in ("0", "-1", "1.001"):
        assert client.post("/api/expenses", json={"category_id": cat["id"], "description": "Bad",
            "amount": amount, "expense_date": "2026-08-27"}).status_code == 422
    changed = client.patch(f"/api/expenses/{item['id']}", json={"description": "Updated", "amount": "12.34"})
    assert changed.status_code == 200 and changed.json()["amount"] == "12.34"
    for field in ("category_id", "description", "amount", "expense_date"):
        assert client.patch(f"/api/expenses/{item['id']}", json={field: None}).status_code == 422
    # Snapshot names are backend-owned and cannot be nulled or overwritten.
    assert client.patch(f"/api/expenses/{item['id']}", json={"category_name": None}).status_code == 422
    assert client.patch(f"/api/expenses/{item['id']}", json={"notes": None}).status_code == 200


def test_same_category_id_does_not_rewrite_historical_snapshot(client):
    cat = category(client)
    item = expense(client, cat["id"])
    assert client.patch(f"/api/expense-categories/{cat['id']}", json={"name": "Electricity"}).status_code == 200
    edited = client.patch(f"/api/expenses/{item['id']}", json={
        "category_id": cat["id"], "description": "Corrected bill", "amount": "1300.00",
        "expense_date": "2026-08-27", "notes": None,
    }).json()
    assert edited["category_name"] == "Utilities"
    other = category(client, "Rent")
    moved = client.patch(f"/api/expenses/{item['id']}", json={"category_id": other["id"]}).json()
    assert moved["category_name"] == "Rent"


def test_history_filters_date_validation_and_pagination(client):
    utilities, rent = category(client), category(client, "Rent")
    first = expense(client, utilities["id"], description="Power Alpha", expense_date="2026-08-26")
    second = expense(client, rent["id"], description="Office Beta", expense_date="2026-08-27")
    assert client.get("/api/expenses", params={"search": first["expense_number"]}).json()["total"] == 1
    assert client.get("/api/expenses", params={"search": "beta"}).json()["items"][0]["id"] == second["id"]
    assert client.get("/api/expenses", params={"category_id": utilities["id"]}).json()["total"] == 1
    assert client.get("/api/expenses", params={"status": "ACTIVE"}).json()["total"] == 2
    assert client.get("/api/expenses", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()["total"] == 1
    assert client.get("/api/expenses", params={"start_date": "2026-08-28", "end_date": "2026-08-27"}).status_code == 422
    page = client.get("/api/expenses", params={"page": 2, "page_size": 1}).json()
    assert page["total"] == 2 and page["pages"] == 2 and len(page["items"]) == 1


def test_void_is_required_atomic_retained_and_excluded(client):
    cat = category(client); item = expense(client, cat["id"])
    assert client.post(f"/api/expenses/{item['id']}/void", json={}).status_code == 422
    voided = client.post(f"/api/expenses/{item['id']}/void", json={"reason": "Duplicate entry"})
    assert voided.status_code == 200 and voided.json()["status"] == "VOIDED"
    assert client.post(f"/api/expenses/{item['id']}/void", json={"reason": "Again"}).status_code == 409
    history = client.get("/api/expenses", params={"status": "VOIDED"}).json()
    assert history["total"] == 1 and history["items"][0]["void_reason"] == "Duplicate entry"
    summary = client.get("/api/reports/expenses", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()
    assert summary == {"total_expenses": "0.00", "expense_count": 0, "categories": []}


def test_expense_breakdown_net_profit_negative_and_incomplete(client, db):
    cat = category(client); expense(client, cat["id"], amount="20.00")
    item = product(db, "Item", "ITEM", 5, 0)
    sale = Sale(receipt_number="EXPENSE-REPORT", subtotal=15, total=15, amount_tendered=15,
                change_due=0, payment_method="cash", created_at=datetime(2026, 8, 27, 4, tzinfo=timezone.utc))
    db.add(sale); db.flush()
    line = SaleItem(sale_id=sale.id, product_id=item.id, product_name=item.name, sku=item.sku,
                    unit_price=Decimal("15"), cost_price=Decimal("10"), quantity=1, line_total=Decimal("15"))
    db.add(line); db.commit()
    summary = client.get("/api/reports/summary", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()
    assert summary["gross_profit"] == "5.00" and summary["operating_expenses"] == "20.00"
    assert summary["net_profit"] == "-15.00" and summary["net_profit_complete"] is True
    assert client.get("/api/reports/expense-breakdown", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json() == [{"category": "Utilities", "amount": "20.00"}]
    line.cost_price = None; db.commit()
    incomplete = client.get("/api/reports/summary", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()
    assert incomplete["profit_complete"] is False and incomplete["net_profit_complete"] is False and incomplete["net_profit"] is None


def test_refund_not_double_deducted_and_inventory_is_not_expense(client, db):
    cat = category(client); expense(client, cat["id"], amount="2.00")
    item = product(db, "Refundable", "REF", 5, 0)
    sale = Sale(receipt_number="RETURN-REPORT", subtotal=25, total=25, amount_tendered=25,
                change_due=0, payment_method="cash", created_at=datetime(2026, 8, 27, 4, tzinfo=timezone.utc))
    db.add(sale); db.flush()
    line = SaleItem(sale_id=sale.id, product_id=item.id, product_name=item.name, sku=item.sku,
                    unit_price=25, cost_price=10, quantity=1, line_total=25)
    db.add(line); db.flush()
    returned = SaleReturn(return_number="RET-ONE", sale_id=sale.id, refund_total=25,
                          created_at=datetime(2026, 8, 27, 5, tzinfo=timezone.utc))
    db.add(returned); db.flush()
    db.add(SaleReturnItem(sale_return_id=returned.id, sale_item_id=line.id, product_id=item.id,
        product_name=item.name, sku=item.sku, unit_price=25, cost_price=10, quantity=1,
        refund_amount=25, return_to_stock=True)); db.commit()
    report = client.get("/api/reports/summary", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()
    assert report["sales_total"] == "0.00" and report["gross_profit"] == "0.00"
    assert report["operating_expenses"] == "2.00" and report["net_profit"] == "-2.00"
    po, _ = draft(client, [item], [2], ["100.00"])
    order(client, po)
    assert receive(client, po, [2]).status_code == 200
    # A real ₱200 inventory receipt changes stock/cost but not operating expense.
    assert client.get("/api/reports/expenses", params={"start_date": "2026-08-27", "end_date": "2026-08-27"}).json()["total_expenses"] == "2.00"
