from decimal import Decimal
from sqlalchemy import func, select
from app.models import Category, InventoryMovement, Product, SaleItem

def product(db, name='Water', sku='W-1', stock=10, cost='10.00', active=True):
    category = db.scalar(select(Category).where(Category.name == 'Drinks'))
    if not category:
        category = Category(name='Drinks'); db.add(category); db.flush()
    item = Product(name=name, sku=sku, category_id=category.id, cost_price=Decimal(cost), selling_price=20, current_stock=stock, minimum_stock=0, is_active=active)
    db.add(item); db.commit(); return item

def draft(client, products, quantities=None, costs=None):
    supplier = client.post('/api/suppliers', json={'name': 'ABC Distributor'}).json()
    quantities = quantities or [10] * len(products); costs = costs or ['14.00'] * len(products)
    response = client.post('/api/purchase-orders', json={'supplier_id': supplier['id'], 'items': [{'product_id': str(p.id), 'quantity': quantities[i], 'unit_cost': costs[i]} for i, p in enumerate(products)]})
    assert response.status_code == 201
    return response.json(), supplier

def order(client, po):
    assert client.post(f"/api/purchase-orders/{po['id']}/mark-ordered").status_code == 200

def receive(client, po, quantities):
    return client.post(f"/api/purchase-orders/{po['id']}/receive", json={'items': [{'item_id': item['id'], 'quantity': quantities[i]} for i, item in enumerate(po['items']) if quantities[i]]})

def test_full_receive_and_zero_stock_cost(client, db):
    p = product(db, stock=0); po, _ = draft(client, [p], [4], ['7.25']); order(client, po)
    response = receive(client, po, [4])
    assert response.status_code == 200 and response.json()['status'] == 'RECEIVED'
    db.refresh(p); assert p.current_stock == 4 and p.cost_price == Decimal('7.25')
    movement = db.scalar(select(InventoryMovement)); assert (movement.stock_before, movement.stock_after, movement.reference_type) == (0, 4, 'PURCHASE_ORDER')
    history = client.get('/api/inventory/movements')
    assert history.status_code == 200
    assert history.json()['items'][0]['po_number'] == po['po_number']

def test_multiple_partial_receives_weighted_average_and_repeat_rejected(client, db):
    p = product(db); po, _ = draft(client, [p]); order(client, po)
    first = receive(client, po, [4]); assert first.json()['status'] == 'PARTIALLY_RECEIVED'
    second = receive(client, first.json(), [6]); assert second.json()['status'] == 'RECEIVED'
    db.refresh(p); assert p.current_stock == 20 and p.cost_price == Decimal('12.00')
    repeat = receive(client, second.json(), [1]); assert repeat.status_code == 409 and repeat.json()['detail'] == 'Purchase order has already been fully received.'

def test_cancelled_po_cannot_be_received(client, db):
    p = product(db); po, _ = draft(client, [p]); order(client, po)
    assert client.post(f"/api/purchase-orders/{po['id']}/cancel").status_code == 200
    assert receive(client, po, [1]).status_code == 409

def test_inactive_product_receive_rolls_back_entire_receipt(client, db):
    first = product(db); second = product(db, 'Coke', 'C-1'); po, _ = draft(client, [first, second], [2, 2]); order(client, po)
    second.is_active = False; db.commit()
    response = receive(client, po, [1, 1])
    assert response.status_code == 409 and response.json()['detail'] == 'Product is inactive.'
    db.expire_all(); assert db.get(Product, first.id).current_stock == 10 and db.get(Product, second.id).current_stock == 10
    assert db.scalar(select(func.count()).select_from(InventoryMovement)) == 0
    assert client.get(f"/api/purchase-orders/{po['id']}").json()['status'] == 'ORDERED'

def test_future_sale_uses_received_weighted_cost_snapshot(client, db):
    p = product(db); po, _ = draft(client, [p]); order(client, po); receive(client, po, [10])
    sale = client.post('/api/sales', json={'items': [{'product_id': str(p.id), 'quantity': 1}], 'amount_tendered': '20.00'})
    assert sale.status_code == 201
    assert db.scalar(select(SaleItem.cost_price)) == Decimal('12.00')

def test_supplier_soft_delete_keeps_po(client, db):
    p = product(db, stock=0); po, supplier = draft(client, [p], [1], ['5'])
    assert po['subtotal'] == '5.00'
    assert client.delete(f"/api/suppliers/{supplier['id']}").json()['is_active'] is False
    assert client.get(f"/api/purchase-orders/{po['id']}").json()['supplier']['name'] == 'ABC Distributor'
