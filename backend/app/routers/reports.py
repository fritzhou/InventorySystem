from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.models import Product, Sale, SaleItem
from app.schemas.report import InventoryStatus, ReportSummary, SalesTrendPoint, StockProduct, TopProduct

router = APIRouter(prefix="/api/reports", tags=["reports"])
CENT = Decimal("0.01")


def _timezone() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().reporting_timezone)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError("Invalid REPORTING_TIMEZONE configuration") from exc


def _range(start_date: date | None, end_date: date | None, *, default_today: bool = False):
    local_today = datetime.now(_timezone()).date()
    if default_today:
        start_date = start_date or local_today
        end_date = end_date or local_today
    else:
        end_date = end_date or local_today
        start_date = start_date or (end_date - timedelta(days=29))
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="From date cannot be after To date")
    start = datetime.combine(start_date, time.min, _timezone()).astimezone(timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, _timezone()).astimezone(timezone.utc)
    return start_date, end_date, start, end


def _inventory(db: Session):
    active = Product.is_active.is_(True)
    return db.execute(select(
        func.count(Product.id), func.coalesce(func.sum(Product.current_stock), 0),
        func.sum(case((Product.current_stock > 0, case((Product.current_stock <= Product.minimum_stock, 1), else_=0)), else_=0)),
        func.sum(case((Product.current_stock == 0, 1), else_=0)),
    ).where(active)).one()


def _summary(db: Session, start: datetime, end: datetime) -> ReportSummary:
    sales_total, transaction_count = db.execute(select(
        func.coalesce(func.sum(Sale.total), 0), func.count(Sale.id)
    ).where(Sale.created_at >= start, Sale.created_at < end)).one()
    items_sold, profit, missing_cost = db.execute(select(
        func.coalesce(func.sum(SaleItem.quantity), 0),
        func.coalesce(func.sum(case((SaleItem.cost_price.is_not(None), (SaleItem.unit_price - SaleItem.cost_price) * SaleItem.quantity), else_=0)), 0),
        func.coalesce(func.sum(case((SaleItem.cost_price.is_(None), 1), else_=0)), 0),
    ).join(Sale).where(Sale.created_at >= start, Sale.created_at < end)).one()
    active, units, low, out = _inventory(db)
    total = Decimal(sales_total).quantize(CENT)
    return ReportSummary(
        sales_total=total, transaction_count=transaction_count, items_sold=items_sold,
        gross_profit=Decimal(profit).quantize(CENT), profit_complete=missing_cost == 0,
        average_transaction_value=(total / transaction_count).quantize(CENT) if transaction_count else Decimal("0.00"),
        total_active_products=active, total_units_in_stock=units, low_stock_count=low or 0, out_of_stock_count=out or 0,
    )


@router.get("/dashboard", response_model=ReportSummary)
def dashboard(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    _, _, start, end = _range(start_date, end_date, default_today=True)
    return _summary(db, start, end)


@router.get("/summary", response_model=ReportSummary)
def summary(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    _, _, start, end = _range(start_date, end_date)
    return _summary(db, start, end)


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def sales_trend(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    first, last, start, end = _range(start_date, end_date)
    rows = db.execute(select(Sale.created_at, Sale.total, func.coalesce(func.sum(SaleItem.quantity), 0))
        .outerjoin(SaleItem).where(Sale.created_at >= start, Sale.created_at < end)
        .group_by(Sale.id).order_by(Sale.created_at)).all()
    values = {first + timedelta(days=i): [Decimal("0.00"), 0, 0] for i in range((last - first).days + 1)}
    for created_at, total, quantity in rows:
        aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
        key = aware.astimezone(_timezone()).date()
        values[key][0] += Decimal(total); values[key][1] += 1; values[key][2] += quantity
    return [SalesTrendPoint(date=day, sales=value[0], transactions=value[1], items_sold=value[2]) for day, value in values.items()]


@router.get("/top-products", response_model=list[TopProduct])
def top_products(start_date: date | None = None, end_date: date | None = None,
                 limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    _, _, start, end = _range(start_date, end_date)
    rows = db.execute(select(SaleItem.product_id, SaleItem.product_name, SaleItem.sku,
        func.sum(SaleItem.quantity), func.sum(SaleItem.line_total)).join(Sale)
        .where(Sale.created_at >= start, Sale.created_at < end)
        .group_by(SaleItem.product_id, SaleItem.product_name, SaleItem.sku)
        .order_by(func.sum(SaleItem.quantity).desc(), func.sum(SaleItem.line_total).desc()).limit(limit)).all()
    return [TopProduct(product_id=r[0], product_name=r[1], sku=r[2], quantity_sold=r[3], revenue=r[4]) for r in rows]


@router.get("/inventory-status", response_model=InventoryStatus)
def inventory_status(db: Session = Depends(get_db)):
    active, units, _, _ = _inventory(db)
    def products(out: bool):
        condition = Product.current_stock == 0 if out else (Product.current_stock > 0) & (Product.current_stock <= Product.minimum_stock)
        rows = db.scalars(select(Product).where(Product.is_active.is_(True), condition).order_by(Product.current_stock, Product.name)).all()
        return [StockProduct(product_id=p.id, product_name=p.name, sku=p.sku, current_stock=p.current_stock, minimum_stock=p.minimum_stock) for p in rows]
    return InventoryStatus(total_active_products=active, total_units_in_stock=units, low_stock=products(False), out_of_stock=products(True))
