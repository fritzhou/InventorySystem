from decimal import Decimal

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "stockflow-api"}


def test_product_lifecycle(client: TestClient) -> None:
    category_response = client.post("/api/categories", json={"name": "Drinks", "description": "Beverages"})
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    payload = {
        "name": "Sparkling Water",
        "sku": "DRINK-001",
        "barcode": "4801234567890",
        "category_id": category_id,
        "cost_price": "12.50",
        "selling_price": "20.00",
        "current_stock": 24,
        "minimum_stock": 5,
    }
    create_response = client.post("/api/products", json=payload)
    assert create_response.status_code == 201
    product = create_response.json()
    assert Decimal(product["selling_price"]) == Decimal("20.00")

    barcode_response = client.get("/api/products/barcode/4801234567890")
    assert barcode_response.status_code == 200
    assert barcode_response.json()["sku"] == "DRINK-001"

    deactivate_response = client.delete(f"/api/products/{product['id']}")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert client.get("/api/products").json() == []
