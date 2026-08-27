import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import InventoryMovement, MovementType, Product, Sale, SaleItem
from app.schemas.sale import CheckoutCreate, SaleRead, SaleSummary, SalesPage

router = APIRouter(prefix="/api/sales", tags=["sales"])
CENT = Decimal("0.01")


def _receipt_number() -> str:
    return f"SF-{uuid.uuid4().hex[:12].upper()}"


@router.get("", response_model=SalesPage)
def list_sales(
    search: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SalesPage:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="From date cannot be after To date")

    filters = []
    if search.strip():
        filters.append(Sale.receipt_number.ilike(f"%{search.strip()}%"))
    if start_date:
        filters.append(Sale.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
    if end_date:
        filters.append(Sale.created_at < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc))

    total_items = db.scalar(select(func.count()).select_from(Sale).where(*filters)) or 0
    item_count = func.coalesce(func.sum(SaleItem.quantity), 0).label("item_count")
    rows = db.execute(
        select(Sale, item_count)
        .outerjoin(SaleItem)
        .where(*filters)
        .group_by(Sale.id)
        .order_by(Sale.created_at.desc(), Sale.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return SalesPage(
        items=[SaleSummary(
            id=sale.id, receipt_number=sale.receipt_number, created_at=sale.created_at,
            payment_method=sale.payment_method, total=sale.total, item_count=count,
        ) for sale, count in rows],
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=(total_items + page_size - 1) // page_size,
    )


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: uuid.UUID, db: Session = Depends(get_db)) -> Sale:
    sale = db.scalar(select(Sale).options(selectinload(Sale.items)).where(Sale.id == sale_id))
    if sale is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return sale


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def checkout(payload: CheckoutCreate, db: Session = Depends(get_db)) -> Sale:
    quantities: dict[uuid.UUID, int] = defaultdict(int)
    for item in payload.items:
        quantities[item.product_id] += item.quantity

    try:
        # FOR UPDATE protects supported production databases. The conditional stock
        # update below is the final atomic guard and also works on SQLite.
        products = {
            product.id: product
            for product in db.scalars(
                select(Product).where(Product.id.in_(quantities)).with_for_update()
            )
        }
        for product_id, quantity in quantities.items():
            product = products.get(product_id)
            if product is None:
                raise HTTPException(status_code=404, detail="Product no longer exists")
            if not product.is_active:
                raise HTTPException(status_code=409, detail=f"Product is inactive: {product.name}")
            if product.current_stock < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock for {product.name}. Available: {product.current_stock}",
                )

        total = sum(
            (products[product_id].selling_price * quantity for product_id, quantity in quantities.items()),
            Decimal("0.00"),
        ).quantize(CENT)
        tendered = payload.amount_tendered.quantize(CENT)
        if tendered < total:
            raise HTTPException(status_code=422, detail="Amount tendered is less than total")

        sale = Sale(
            receipt_number=_receipt_number(), subtotal=total, total=total,
            amount_tendered=tendered, change_due=(tendered - total).quantize(CENT), payment_method="cash",
        )
        db.add(sale)
        db.flush()
        for product_id, quantity in quantities.items():
            product = products[product_id]
            stock_before = product.current_stock
            stock_after = stock_before - quantity
            line_total = (product.selling_price * quantity).quantize(CENT)
            result = db.execute(
                update(Product)
                .where(Product.id == product_id, Product.is_active.is_(True), Product.current_stock == stock_before)
                .values(current_stock=stock_after)
            )
            if result.rowcount != 1:
                db.refresh(product)
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock for {product.name}. Available: {product.current_stock}",
                )
            sale.items.append(SaleItem(
                product_id=product.id, product_name=product.name, sku=product.sku,
                unit_price=product.selling_price, quantity=quantity, line_total=line_total,
            ))
            db.add(InventoryMovement(
                product_id=product.id, movement_type=MovementType.SALE, quantity_change=-quantity,
                stock_before=stock_before, stock_after=stock_after,
                reference_type="SALE", reference_id=sale.id,
            ))
        db.commit()
        db.refresh(sale)
        return sale
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Checkout could not be completed. No stock was changed.") from exc
