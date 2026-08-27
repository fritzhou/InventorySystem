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


def test_product_search_filter_update_and_duplicate_validation(client: TestClient) -> None:
    drinks = client.post("/api/categories", json={"name": " Drinks ", "description": " Beverages "}).json()
    snacks = client.post("/api/categories", json={"name": "Snacks"}).json()
    base_product = {
        "name": "Sparkling Water",
        "sku": "DRINK-001",
        "barcode": "4801234567890",
        "category_id": drinks["id"],
        "cost_price": "12.50",
        "selling_price": "20.00",
        "current_stock": 3,
        "minimum_stock": 5,
    }
    product = client.post("/api/products", json=base_product).json()
    client.post("/api/products", json={**base_product, "name": "Chips", "sku": "SNACK-001", "barcode": None, "category_id": snacks["id"]})

    filtered = client.get("/api/products", params={"search": "480123", "category_id": drinks["id"]})
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [product["id"]]

    updated = client.patch(
        f"/api/products/{product['id']}",
        json={"name": " Mineral Water ", "sku": "DRINK-002", "barcode": " ", "selling_price": "22.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Mineral Water"
    assert updated.json()["sku"] == "DRINK-002"
    assert updated.json()["barcode"] is None
    assert updated.json()["current_stock"] == 3

    duplicate = client.post("/api/products", json={**base_product, "sku": "DRINK-002", "barcode": None})
    assert duplicate.status_code == 409


def test_rejects_blank_category_and_invalid_product_values(client: TestClient) -> None:
    assert client.post("/api/categories", json={"name": "   "}).status_code == 422
    category_id = client.post("/api/categories", json={"name": "Drinks"}).json()["id"]
    invalid = client.post(
        "/api/products",
        json={
            "name": "Water",
            "sku": "WATER-001",
            "category_id": category_id,
            "cost_price": "-1.00",
            "selling_price": "2.00",
            "current_stock": -1,
            "minimum_stock": 0,
        },
    )
    assert invalid.status_code == 422
