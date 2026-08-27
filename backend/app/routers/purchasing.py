import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.dependencies.auth import manager_role
from app.models import InventoryMovement, MovementType, Product, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus, Supplier
from app.schemas.purchasing import POCreate, POPage, PORead, POUpdate, ReceiveInput, SupplierInput, SupplierPage, SupplierRead, SupplierUpdate

router=APIRouter(tags=["purchasing"], dependencies=[Depends(manager_role)]); MONEY=Decimal("0.01")
def fail(code,msg): raise HTTPException(status_code=code,detail=msg)
def supplier_or_404(db,id,active=False):
    obj=db.get(Supplier,id)
    if not obj: fail(404,"Supplier not found.")
    if active and not obj.is_active: fail(409,"Supplier is inactive.")
    return obj
def po_query(lock=False):
    q=select(PurchaseOrder).options(selectinload(PurchaseOrder.supplier),selectinload(PurchaseOrder.items))
    return q.with_for_update() if lock else q
def po_or_404(db,id,lock=False):
    obj=db.scalar(po_query(lock).where(PurchaseOrder.id==id))
    if not obj: fail(404,"Purchase order not found.")
    return obj
def set_items(db,po,payload):
    seen=set(); built=[]; subtotal=Decimal("0")
    for line in payload.items:
        if line.product_id in seen: fail(422,"Duplicate product lines are not allowed.")
        seen.add(line.product_id); product=db.get(Product,line.product_id)
        if not product: fail(404,"Product not found.")
        if not product.is_active: fail(409,"Product is inactive.")
        total=(Decimal(line.unit_cost)*line.quantity).quantize(MONEY)
        built.append(PurchaseOrderItem(product_id=product.id,product_name=product.name,sku=product.sku,ordered_quantity=line.quantity,received_quantity=0,unit_cost=line.unit_cost,line_total=total)); subtotal+=total
    po.items=built; po.subtotal=subtotal.quantize(MONEY)

@router.get("/api/suppliers",response_model=SupplierPage)
def suppliers(search:str="",active_only:bool=True,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    f=[]
    if active_only:f.append(Supplier.is_active.is_(True))
    if search.strip(): f.append(or_(Supplier.name.ilike(f"%{search.strip()}%"),Supplier.contact_person.ilike(f"%{search.strip()}%")))
    total=db.scalar(select(func.count()).select_from(Supplier).where(*f)) or 0
    items=list(db.scalars(select(Supplier).where(*f).order_by(Supplier.name).offset((page-1)*page_size).limit(page_size)))
    return SupplierPage(items=items,page=page,page_size=page_size,total_items=total,total_pages=(total+page_size-1)//page_size)
@router.post("/api/suppliers",response_model=SupplierRead,status_code=201)
def create_supplier(payload:SupplierInput,db:Session=Depends(get_db)):
    if db.scalar(select(Supplier).where(func.lower(Supplier.name)==payload.name.lower())): fail(409,"A supplier with this name already exists.")
    obj=Supplier(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
@router.get("/api/suppliers/{id}",response_model=SupplierRead)
def get_supplier(id:uuid.UUID,db:Session=Depends(get_db)): return supplier_or_404(db,id)
@router.patch("/api/suppliers/{id}",response_model=SupplierRead)
def patch_supplier(id:uuid.UUID,payload:SupplierUpdate,db:Session=Depends(get_db)):
    obj=supplier_or_404(db,id)
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(obj,k,v.strip() if isinstance(v,str) else v)
    if not obj.name: fail(422,"Supplier name is required.")
    try: db.commit()
    except IntegrityError: db.rollback(); fail(409,"A supplier with this name already exists.")
    db.refresh(obj); return obj
@router.delete("/api/suppliers/{id}",response_model=SupplierRead)
def delete_supplier(id:uuid.UUID,db:Session=Depends(get_db)):
    obj=supplier_or_404(db,id); obj.is_active=False; db.commit(); db.refresh(obj); return obj

@router.get("/api/purchase-orders",response_model=POPage)
def list_pos(search:str="",supplier_id:uuid.UUID|None=None,status_filter:PurchaseOrderStatus|None=Query(None,alias="status"),from_date:date|None=None,to_date:date|None=None,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    if from_date and to_date and from_date>to_date: fail(422,"From date cannot be after To date.")
    f=[]
    if search.strip():f.append(PurchaseOrder.po_number.ilike(f"%{search.strip()}%"))
    if supplier_id:f.append(PurchaseOrder.supplier_id==supplier_id)
    if status_filter:f.append(PurchaseOrder.status==status_filter)
    if from_date:f.append(PurchaseOrder.order_date>=from_date)
    if to_date:f.append(PurchaseOrder.order_date<=to_date)
    total=db.scalar(select(func.count()).select_from(PurchaseOrder).where(*f)) or 0
    items=list(db.scalars(po_query().where(*f).order_by(PurchaseOrder.order_date.desc(),PurchaseOrder.po_number.desc()).offset((page-1)*page_size).limit(page_size)))
    return POPage(items=items,page=page,page_size=page_size,total_items=total,total_pages=(total+page_size-1)//page_size)
@router.post("/api/purchase-orders",response_model=PORead,status_code=201)
def create_po(payload:POCreate,db:Session=Depends(get_db)):
    supplier_or_404(db,payload.supplier_id,True)
    po=PurchaseOrder(po_number=f"PO-{date.today():%Y%m%d}-{token_hex(2).upper()}",supplier_id=payload.supplier_id,expected_date=payload.expected_date,notes=payload.notes,subtotal=0)
    set_items(db,po,payload); db.add(po)
    try: db.commit()
    except IntegrityError: db.rollback(); fail(409,"Purchase order could not be created. Please try again.")
    return po_or_404(db,po.id)
@router.get("/api/purchase-orders/{id}",response_model=PORead)
def get_po(id:uuid.UUID,db:Session=Depends(get_db)): return po_or_404(db,id)
@router.patch("/api/purchase-orders/{id}",response_model=PORead)
def patch_po(id:uuid.UUID,payload:POUpdate,db:Session=Depends(get_db)):
    po=po_or_404(db,id)
    if po.status!=PurchaseOrderStatus.DRAFT: fail(409,"Only draft purchase orders may be edited.")
    supplier_or_404(db,payload.supplier_id,True); po.supplier_id=payload.supplier_id; po.expected_date=payload.expected_date; po.notes=payload.notes; set_items(db,po,payload); db.commit(); return po_or_404(db,id)
@router.post("/api/purchase-orders/{id}/mark-ordered",response_model=PORead)
def mark_ordered(id:uuid.UUID,db:Session=Depends(get_db)):
    po=po_or_404(db,id,True)
    if po.status!=PurchaseOrderStatus.DRAFT: fail(409,"Only a draft purchase order may be marked as ordered.")
    po.status=PurchaseOrderStatus.ORDERED; db.commit(); return po_or_404(db,id)
@router.post("/api/purchase-orders/{id}/cancel",response_model=PORead)
def cancel(id:uuid.UUID,db:Session=Depends(get_db)):
    po=po_or_404(db,id,True)
    if po.status not in (PurchaseOrderStatus.DRAFT,PurchaseOrderStatus.ORDERED) or any(x.received_quantity for x in po.items): fail(409,"Purchase order cannot be cancelled after stock has been received.")
    po.status=PurchaseOrderStatus.CANCELLED; db.commit(); return po_or_404(db,id)
@router.post("/api/purchase-orders/{id}/receive",response_model=PORead)
def receive(id:uuid.UUID,payload:ReceiveInput,db:Session=Depends(get_db)):
    try:
        po=po_or_404(db,id,True)
        if po.status==PurchaseOrderStatus.RECEIVED: fail(409,"Purchase order has already been fully received.")
        if po.status not in (PurchaseOrderStatus.ORDERED,PurchaseOrderStatus.PARTIALLY_RECEIVED): fail(409,"Purchase order cannot be received in its current status.")
        lines={x.id:x for x in po.items}; seen=set()
        for req in payload.items:
            if req.item_id in seen: fail(422,"Duplicate receiving lines are not allowed.")
            seen.add(req.item_id); line=lines.get(req.item_id)
            if not line: fail(422,"Purchase order item not found.")
            remaining=line.ordered_quantity-line.received_quantity
            if req.quantity>remaining: fail(409,f"Cannot receive {req.quantity} units. Only {remaining} remain on this purchase order.")
        for req in payload.items:
            line=lines[req.item_id]; product=db.scalar(select(Product).where(Product.id==line.product_id).with_for_update())
            if not product: fail(409,"Product no longer exists.")
            if not product.is_active: fail(409,"Product is inactive.")
            before=product.current_stock; after=before+req.quantity; old_cost=Decimal(product.cost_price)
            average=(Decimal(line.unit_cost) if before==0 else ((before*old_cost)+(req.quantity*Decimal(line.unit_cost)))/after).quantize(MONEY,rounding=ROUND_HALF_UP)
            result=db.execute(update(Product).where(
                Product.id == product.id,
                Product.current_stock == before,
                Product.is_active.is_(True),
            ).values(current_stock=after, cost_price=average))
            if result.rowcount!=1: fail(409,"Inventory changed while receiving. Please try again.")
            line.received_quantity+=req.quantity
            db.add(InventoryMovement(product_id=product.id,movement_type=MovementType.RESTOCK,quantity_change=req.quantity,stock_before=before,stock_after=after,reference_type="PURCHASE_ORDER",reference_id=po.id,note=f"Received on {po.po_number}"))
        po.status=PurchaseOrderStatus.RECEIVED if all(x.received_quantity==x.ordered_quantity for x in po.items) else PurchaseOrderStatus.PARTIALLY_RECEIVED
        db.commit(); return po_or_404(db,id)
    except HTTPException: db.rollback(); raise
    except SQLAlchemyError as exc: db.rollback(); raise HTTPException(500,"Purchase order could not be received.") from exc
