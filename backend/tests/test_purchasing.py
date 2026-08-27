from decimal import Decimal
from app.models import Category, Product, InventoryMovement

def product(db, stock=10, cost='10.00'):
    c=Category(name='Drinks'); db.add(c); db.flush(); p=Product(name='Water',sku='W-1',category_id=c.id,cost_price=Decimal(cost),selling_price=20,current_stock=stock,minimum_stock=0); db.add(p); db.commit(); return p

def test_supplier_po_partial_receive_and_weighted_cost(client,db):
    p=product(db)
    supplier=client.post('/api/suppliers',json={'name':'ABC Distributor'}).json()
    response=client.post('/api/purchase-orders',json={'supplier_id':supplier['id'],'items':[{'product_id':str(p.id),'quantity':10,'unit_cost':'14.00'}]})
    assert response.status_code==201
    po=response.json(); assert po['subtotal']=='140.00' and po['status']=='DRAFT'
    assert client.post(f"/api/purchase-orders/{po['id']}/mark-ordered").status_code==200
    item=po['items'][0]
    received=client.post(f"/api/purchase-orders/{po['id']}/receive",json={'items':[{'item_id':item['id'],'quantity':5}]})
    assert received.json()['status']=='PARTIALLY_RECEIVED'
    db.refresh(p); assert p.current_stock==15 and p.cost_price==Decimal('11.33')
    movement=db.query(InventoryMovement).one(); assert (movement.stock_before,movement.stock_after,movement.reference_type)==(10,15,'PURCHASE_ORDER')
    over=client.post(f"/api/purchase-orders/{po['id']}/receive",json={'items':[{'item_id':item['id'],'quantity':6}]})
    assert over.status_code==409
    db.refresh(p); assert p.current_stock==15

def test_supplier_soft_delete_keeps_po(client,db):
    p=product(db,0)
    supplier=client.post('/api/suppliers',json={'name':'Historic Supplier'}).json()
    po=client.post('/api/purchase-orders',json={'supplier_id':supplier['id'],'items':[{'product_id':str(p.id),'quantity':1,'unit_cost':'5'}]}).json()
    assert client.delete(f"/api/suppliers/{supplier['id']}").json()['is_active'] is False
    assert client.get(f"/api/purchase-orders/{po['id']}").json()['supplier']['name']=='Historic Supplier'
