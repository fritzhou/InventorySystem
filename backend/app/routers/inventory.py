import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import InventoryMovement, MovementType, Product, Sale, PurchaseOrder
from app.schemas.inventory import InventoryMovementPage, InventoryMovementRead, StockAdjustmentCreate

router = APIRouter(tags=["inventory"])


@router.post("/api/products/{product_id}/stock-adjustments", response_model=InventoryMovementRead, status_code=status.HTTP_201_CREATED)
def adjust_stock(product_id: uuid.UUID, payload: StockAdjustmentCreate, db: Session = Depends(get_db)) -> InventoryMovementRead:
    try:
        product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
        if not product.is_active:
            raise HTTPException(status_code=409, detail="Product is inactive.")
        before = product.current_stock
        if payload.type == MovementType.RESTOCK:
            change = payload.quantity or 0
        elif payload.type == MovementType.DAMAGE:
            change = -(payload.quantity or 0)
        else:
            change = (payload.actual_stock or 0) - before
        after = before + change
        if after < 0:
            raise HTTPException(status_code=409, detail=f"Cannot remove {abs(change)} items. Only {before} are currently in stock.")
        result = db.execute(update(Product).where(Product.id == product_id, Product.current_stock == before, Product.is_active.is_(True)).values(current_stock=after))
        if result.rowcount != 1:
            raise HTTPException(status_code=409, detail="Stock changed while this adjustment was being saved. Please try again.")
        movement = InventoryMovement(product_id=product.id, movement_type=payload.type, quantity_change=change,
                                     stock_before=before, stock_after=after, note=payload.note)
        db.add(movement)
        db.commit()
        db.refresh(movement)
        movement.product = product
        product.current_stock = after
        return InventoryMovementRead.model_validate(movement)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Stock adjustment could not be completed.") from exc


@router.get("/api/inventory/movements", response_model=InventoryMovementPage)
def list_movements(product_id: uuid.UUID | None = None, movement_type: MovementType | None = None,
                   search: str = "", start_date: date | None = None, end_date: date | None = None,
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db)) -> InventoryMovementPage:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="From date cannot be after To date")
    filters = []
    if product_id:
        filters.append(InventoryMovement.product_id == product_id)
    if movement_type:
        filters.append(InventoryMovement.movement_type == movement_type)
    if search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    if start_date:
        filters.append(InventoryMovement.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
    if end_date:
        filters.append(InventoryMovement.created_at < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc))
    total = db.scalar(select(func.count()).select_from(InventoryMovement).join(Product).where(*filters)) or 0
    movements = list(db.scalars(select(InventoryMovement).join(Product).options(selectinload(InventoryMovement.product))
        .where(*filters).order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
        .offset((page - 1) * page_size).limit(page_size)))
    sale_ids = [m.reference_id for m in movements if m.reference_type == "SALE" and m.reference_id]
    receipts = dict(db.execute(select(Sale.id, Sale.receipt_number).where(Sale.id.in_(sale_ids))).all()) if sale_ids else {}
    po_ids = [m.reference_id for m in movements if m.reference_type == "PURCHASE_ORDER" and m.reference_id]
    po_numbers = dict(db.execute(select(PurchaseOrder.id, PurchaseOrder.po_number).where(PurchaseOrder.id.in_(po_ids))).all()) if po_ids else {}
    items = []
    for movement in movements:
        item = InventoryMovementRead.model_validate(movement)
        item.receipt_number = receipts.get(movement.reference_id)
        item.po_number = po_numbers.get(movement.reference_id)
        items.append(item)
    return InventoryMovementPage(items=items, page=page, page_size=page_size, total_items=total,
                                 total_pages=(total + page_size - 1) // page_size)
