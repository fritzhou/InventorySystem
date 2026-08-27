from decimal import Decimal

from sqlalchemy import select

from app.models import Category, InventoryMovement, Product
from app.models.user import AuditEvent


def product(db):
    category = Category(name="Phase 11")
    db.add(category); db.flush()
    item = Product(name="Safe Product", sku="SAFE-1", barcode="123456789", category_id=category.id,
                   cost_price=Decimal("4.00"), selling_price=Decimal("7.00"), current_stock=10, minimum_stock=2)
    db.add(item); db.commit(); return item


def test_cashier_product_payloads_never_expose_cost(cashier_client, db):
    item = product(db)
    responses = [cashier_client.get("/api/products"), cashier_client.get(f"/api/products/barcode/{item.barcode}"),
                 cashier_client.get(f"/api/products/barcode/{item.barcode}/lookup")]
    assert all(response.status_code == 200 for response in responses)
    assert "cost_price" not in responses[0].json()[0]
    assert "cost_price" not in responses[1].json()
    assert "cost_price" not in responses[2].json()["product"]


def test_manager_product_payload_and_actor_audit(manager_client, db):
    item = product(db)
    actor_id = manager_client.get("/api/auth/me").json()["id"]
    response = manager_client.patch(f"/api/products/{item.id}", json={"name":"Updated", "actor_user_id":"00000000-0000-0000-0000-000000000001"})
    assert response.status_code == 422
    response = manager_client.patch(f"/api/products/{item.id}", json={"name":"Updated"})
    assert response.status_code == 200 and response.json()["cost_price"] == "4.00"
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "PRODUCT_UPDATED"))
    assert str(event.actor_user_id) == actor_id


def test_cashier_forbidden_operational_and_admin_apis(cashier_client, db):
    item = product(db)
    checks = [("post", f"/api/products/{item.id}/stock-adjustments", {"json":{"type":"RESTOCK","quantity":1}}),
              ("get", "/api/suppliers", {}), ("get", "/api/purchase-orders", {}), ("get", "/api/expenses", {}),
              ("get", "/api/reports/summary", {}), ("get", "/api/users", {}), ("get", "/api/audit-events", {})]
    for method, url, kwargs in checks:
        assert getattr(cashier_client, method)(url, **kwargs).status_code == 403


def test_manager_cannot_access_admin_financial_apis(manager_client):
    for url in ("/api/expenses", "/api/reports/summary", "/api/users", "/api/audit-events"):
        assert manager_client.get(url).status_code == 403


def test_unauthenticated_business_request_is_401(unauthenticated_client):
    assert unauthenticated_client.get("/api/products").status_code == 401


def test_po_receiving_uses_authenticated_actor(manager_client, db):
    item = product(db); actor_id = manager_client.get("/api/auth/me").json()["id"]
    supplier = manager_client.post("/api/suppliers", json={"name":"Supplier"}).json()
    po = manager_client.post("/api/purchase-orders", json={"supplier_id":supplier["id"],"items":[{"product_id":str(item.id),"quantity":2,"unit_cost":"5.00"}]}).json()
    assert manager_client.post(f"/api/purchase-orders/{po['id']}/mark-ordered").status_code == 200
    po = manager_client.get(f"/api/purchase-orders/{po['id']}").json()
    response = manager_client.post(f"/api/purchase-orders/{po['id']}/receive", json={"items":[{"item_id":po["items"][0]["id"],"quantity":1}]})
    assert response.status_code == 200
    movement = db.scalar(select(InventoryMovement).where(InventoryMovement.reference_type == "PURCHASE_ORDER"))
    assert str(movement.actor_user_id) == actor_id
    actions = set(db.scalars(select(AuditEvent.action)))
    assert {"SUPPLIER_CREATED","PURCHASE_ORDER_CREATED","PURCHASE_ORDER_ORDERED","PURCHASE_ORDER_RECEIVED"} <= actions
