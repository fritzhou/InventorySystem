import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.auth import manager_role
from app.models.user import User
from app.audit import record_audit
from app.core.config import get_settings
from app.models import InventoryMovement, MovementType, Product, Sale, SaleItem, SaleReturn, SaleReturnItem
from app.schemas.return_ import ReturnsPage, SaleReturnCreate, SaleReturnRead

router = APIRouter(tags=["returns"], dependencies=[Depends(manager_role)])
CENT = Decimal("0.01")


def _business_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().reporting_timezone)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError("Invalid REPORTING_TIMEZONE configuration") from exc


def _return_number() -> str:
    return f"RTN-{datetime.now(_business_timezone()):%Y%m%d}-{uuid.uuid4().hex[:4].upper()}"


def _loaded_return(db: Session, return_id: uuid.UUID):
    return db.scalar(select(SaleReturn).options(selectinload(SaleReturn.items), selectinload(SaleReturn.sale)).where(SaleReturn.id == return_id))


@router.post("/api/sales/{sale_id}/returns", response_model=SaleReturnRead, status_code=status.HTTP_201_CREATED)
def create_return(sale_id: uuid.UUID, payload: SaleReturnCreate, db: Session = Depends(get_db), actor: User = Depends(manager_role)):
    ids = [item.sale_item_id for item in payload.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="A sale item may only appear once in a return request.")
    try:
        sale = db.scalar(select(Sale).where(Sale.id == sale_id).with_for_update())
        if sale is None:
            raise HTTPException(status_code=404, detail="Sale not found.")
        sale_items = {item.id: item for item in db.scalars(select(SaleItem).where(SaleItem.id.in_(ids)).with_for_update())}
        prior = dict(db.execute(select(SaleReturnItem.sale_item_id, func.sum(SaleReturnItem.quantity))
            .where(SaleReturnItem.sale_item_id.in_(ids)).group_by(SaleReturnItem.sale_item_id)).all())
        products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_([i.product_id for i in sale_items.values()])).with_for_update())}
        total = Decimal("0.00")
        prepared = []
        for requested in payload.items:
            original = sale_items.get(requested.sale_item_id)
            if original is None or original.sale_id != sale_id:
                raise HTTPException(status_code=422, detail="Sale item does not belong to this sale.")
            remaining = original.quantity - int(prior.get(original.id, 0))
            if remaining == 0:
                raise HTTPException(status_code=409, detail="This item has already been fully returned.")
            if requested.quantity > remaining:
                raise HTTPException(status_code=409, detail=f"Returned quantity exceeds the remaining returnable quantity. Available: {remaining}.")
            product = products.get(original.product_id)
            if requested.return_to_stock and (product is None or not product.is_active):
                raise HTTPException(status_code=409, detail="Cannot return this item to stock because the product is inactive.")
            refund = (original.unit_price * requested.quantity).quantize(CENT)
            total += refund
            prepared.append((requested, original, product, refund))

        returned = SaleReturn(return_number=_return_number(), sale_id=sale.id, refund_total=total.quantize(CENT), reason=payload.reason or None, processed_by_user_id=actor.id)
        db.add(returned); db.flush()
        for requested, original, product, refund in prepared:
            db.add(SaleReturnItem(sale_return_id=returned.id, sale_item_id=original.id, product_id=original.product_id,
                product_name=original.product_name, sku=original.sku, unit_price=original.unit_price,
                cost_price=original.cost_price, quantity=requested.quantity, refund_amount=refund,
                return_to_stock=requested.return_to_stock))
            if requested.return_to_stock:
                before = product.current_stock
                after = before + requested.quantity
                current_cost = Decimal(product.cost_price)
                # Legacy sale items may not have a trustworthy cost snapshot. In
                # that case stock is returned while the current average cost is
                # deliberately preserved rather than inventing historical cost.
                average_cost = current_cost
                if original.cost_price is not None:
                    historical_cost = Decimal(original.cost_price)
                    average_cost = (historical_cost if before == 0 else
                        ((before * current_cost) + (requested.quantity * historical_cost)) / after
                    ).quantize(CENT, rounding=ROUND_HALF_UP)
                result = db.execute(update(Product).where(
                    Product.id == product.id, Product.is_active.is_(True),
                    Product.current_stock == before, Product.cost_price == current_cost,
                ).values(current_stock=after, cost_price=average_cost))
                if result.rowcount != 1:
                    raise HTTPException(status_code=409, detail="Product stock changed while processing the return. Please retry.")
                db.add(InventoryMovement(product_id=product.id, movement_type=MovementType.RETURN, actor_user_id=actor.id,
                    quantity_change=requested.quantity, stock_before=before, stock_after=after,
                    reference_type="SALE_RETURN", reference_id=returned.id, note=returned.return_number))
        record_audit(db, actor, "RETURN_CREATED", "RETURN", returned.id)
        db.commit()
        return _loaded_return(db, returned.id)
    except HTTPException:
        db.rollback(); raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Return conflicts with another return. Please refresh and retry.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Return could not be processed.") from exc


@router.get("/api/sales/{sale_id}/returns", response_model=list[SaleReturnRead])
def sale_returns(sale_id: uuid.UUID, db: Session = Depends(get_db)):
    if db.get(Sale, sale_id) is None:
        raise HTTPException(status_code=404, detail="Sale not found.")
    return db.scalars(select(SaleReturn).options(selectinload(SaleReturn.items), selectinload(SaleReturn.sale))
        .where(SaleReturn.sale_id == sale_id).order_by(SaleReturn.created_at.desc())).all()


@router.get("/api/returns", response_model=ReturnsPage)
def list_returns(search: str = "", start_date: date | None = None, end_date: date | None = None,
                 page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="From date cannot be after To date")
    filters = []
    if search.strip(): filters.append(or_(SaleReturn.return_number.ilike(f"%{search.strip()}%"), Sale.receipt_number.ilike(f"%{search.strip()}%")))
    business_tz = _business_timezone()
    if start_date:
        filters.append(SaleReturn.created_at >= datetime.combine(start_date, time.min, business_tz).astimezone(timezone.utc))
    if end_date:
        filters.append(SaleReturn.created_at < datetime.combine(end_date + timedelta(days=1), time.min, business_tz).astimezone(timezone.utc))
    base = select(SaleReturn).join(Sale).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.options(selectinload(SaleReturn.items), selectinload(SaleReturn.sale))
        .order_by(SaleReturn.created_at.desc(), SaleReturn.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ReturnsPage(items=items, page=page, page_size=page_size, total_items=total, total_pages=(total + page_size - 1) // page_size)


@router.get("/api/returns/{return_id}", response_model=SaleReturnRead)
def get_return(return_id: uuid.UUID, db: Session = Depends(get_db)):
    result = _loaded_return(db, return_id)
    if result is None: raise HTTPException(status_code=404, detail="Return not found.")
    return result
