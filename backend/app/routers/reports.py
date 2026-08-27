from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.models import Expense, ExpenseStatus, Product, Sale, SaleItem, SaleReturn, SaleReturnItem
from app.schemas.report import ExpenseBreakdownItem, ExpenseSummary, InventoryStatus, ReportSummary, SalesTrendPoint, StockProduct, TopProduct

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


def _expense_rows(db: Session, first: date, last: date):
    return db.execute(select(Expense.category_name, func.sum(Expense.amount)).where(
        Expense.status == ExpenseStatus.ACTIVE, Expense.expense_date >= first, Expense.expense_date <= last
    ).group_by(Expense.category_name).order_by(func.sum(Expense.amount).desc(), Expense.category_name)).all()


def _summary(db: Session, first: date, last: date, start: datetime, end: datetime) -> ReportSummary:
    sales_total, transaction_count = db.execute(select(
        func.coalesce(func.sum(Sale.total), 0), func.count(Sale.id)
    ).where(Sale.created_at >= start, Sale.created_at < end)).one()
    items_sold, profit, missing_cost = db.execute(select(
        func.coalesce(func.sum(SaleItem.quantity), 0),
        func.coalesce(func.sum(case((SaleItem.cost_price.is_not(None), (SaleItem.unit_price - SaleItem.cost_price) * SaleItem.quantity), else_=0)), 0),
        func.coalesce(func.sum(case((SaleItem.cost_price.is_(None), 1), else_=0)), 0),
    ).join(Sale).where(Sale.created_at >= start, Sale.created_at < end)).one()
    refunds, returned_items, reversed_profit, missing_return_cost = db.execute(select(
        func.coalesce(func.sum(SaleReturnItem.refund_amount), 0),
        func.coalesce(func.sum(SaleReturnItem.quantity), 0),
        func.coalesce(func.sum(case((SaleReturnItem.cost_price.is_not(None), (SaleReturnItem.unit_price - SaleReturnItem.cost_price) * SaleReturnItem.quantity), else_=0)), 0),
        func.coalesce(func.sum(case((SaleReturnItem.cost_price.is_(None), 1), else_=0)), 0),
    ).join(SaleReturn).where(SaleReturn.created_at >= start, SaleReturn.created_at < end)).one()
    active, units, low, out = _inventory(db)
    total = (Decimal(sales_total) - Decimal(refunds)).quantize(CENT)
    operating_expenses = sum((Decimal(row[1]) for row in _expense_rows(db, first, last)), Decimal("0.00")).quantize(CENT)
    gross_profit = (Decimal(profit) - Decimal(reversed_profit)).quantize(CENT)
    complete = missing_cost == 0 and missing_return_cost == 0
    return ReportSummary(
        sales_total=total, transaction_count=transaction_count, items_sold=items_sold - returned_items,
        gross_profit=gross_profit, profit_complete=complete, operating_expenses=operating_expenses,
        net_profit=(gross_profit - operating_expenses).quantize(CENT) if complete else None, net_profit_complete=complete,
        average_transaction_value=(total / transaction_count).quantize(CENT) if transaction_count else Decimal("0.00"),
        total_active_products=active, total_units_in_stock=units, low_stock_count=low or 0, out_of_stock_count=out or 0,
    )


@router.get("/dashboard", response_model=ReportSummary)
def dashboard(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    first, last, start, end = _range(start_date, end_date, default_today=True)
    return _summary(db, first, last, start, end)


@router.get("/summary", response_model=ReportSummary)
def summary(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    first, last, start, end = _range(start_date, end_date)
    return _summary(db, first, last, start, end)


@router.get("/expenses", response_model=ExpenseSummary)
def expense_summary(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    first, last, _, _ = _range(start_date, end_date)
    rows = _expense_rows(db, first, last)
    count = db.scalar(select(func.count(Expense.id)).where(Expense.status == ExpenseStatus.ACTIVE,
        Expense.expense_date >= first, Expense.expense_date <= last)) or 0
    categories = [ExpenseBreakdownItem(category=name, amount=amount) for name, amount in rows]
    return ExpenseSummary(total_expenses=sum((Decimal(x.amount) for x in categories), Decimal("0.00")), expense_count=count, categories=categories)


@router.get("/expense-breakdown", response_model=list[ExpenseBreakdownItem])
def expense_breakdown(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    first, last, _, _ = _range(start_date, end_date)
    return [ExpenseBreakdownItem(category=name, amount=amount) for name, amount in _expense_rows(db, first, last)]


@router.get("/sales-trend", response_model=list[SalesTrendPoint])
def sales_trend(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    first, last, start, end = _range(start_date, end_date)
    rows = db.execute(select(Sale.created_at, Sale.total, func.coalesce(func.sum(SaleItem.quantity), 0))
        .outerjoin(SaleItem).where(Sale.created_at >= start, Sale.created_at < end)
        .group_by(Sale.id).order_by(Sale.created_at)).all()
    # sales, transactions, items, gross profit, missing-cost rows, expenses
    values = {first + timedelta(days=i): [Decimal("0.00"), 0, 0, Decimal("0.00"), 0, Decimal("0.00")] for i in range((last - first).days + 1)}
    for created_at, total, quantity in rows:
        aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
        key = aware.astimezone(_timezone()).date()
        values[key][0] += Decimal(total); values[key][1] += 1; values[key][2] += quantity
    profit_rows = db.execute(select(Sale.created_at, SaleItem.unit_price, SaleItem.cost_price, SaleItem.quantity).join(Sale)
        .where(Sale.created_at >= start, Sale.created_at < end)).all()
    for created_at, price, cost, quantity in profit_rows:
        aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at; key = aware.astimezone(_timezone()).date()
        if cost is None: values[key][4] += 1
        else: values[key][3] += (Decimal(price) - Decimal(cost)) * quantity
    returns = db.execute(select(SaleReturn.created_at, SaleReturn.refund_total, func.coalesce(func.sum(SaleReturnItem.quantity), 0))
        .outerjoin(SaleReturnItem).where(SaleReturn.created_at >= start, SaleReturn.created_at < end)
        .group_by(SaleReturn.id).order_by(SaleReturn.created_at)).all()
    for created_at, refund, quantity in returns:
        aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
        key = aware.astimezone(_timezone()).date()
        values[key][0] -= Decimal(refund); values[key][2] -= quantity
    return_profit_rows = db.execute(select(SaleReturn.created_at, SaleReturnItem.unit_price, SaleReturnItem.cost_price, SaleReturnItem.quantity).join(SaleReturn)
        .where(SaleReturn.created_at >= start, SaleReturn.created_at < end)).all()
    for created_at, price, cost, quantity in return_profit_rows:
        aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at; key = aware.astimezone(_timezone()).date()
        if cost is None: values[key][4] += 1
        else: values[key][3] -= (Decimal(price) - Decimal(cost)) * quantity
    for expense_date, amount in db.execute(select(Expense.expense_date, func.sum(Expense.amount)).where(
        Expense.status == ExpenseStatus.ACTIVE, Expense.expense_date >= first, Expense.expense_date <= last).group_by(Expense.expense_date)):
        values[expense_date][5] = Decimal(amount)
    return [SalesTrendPoint(date=day, sales=v[0], transactions=v[1], items_sold=v[2], gross_profit=v[3], expenses=v[5],
        net_profit=(v[3]-v[5]) if v[4] == 0 else None, profit_complete=v[4] == 0) for day, v in values.items()]


@router.get("/top-products", response_model=list[TopProduct])
def top_products(start_date: date | None = None, end_date: date | None = None,
                 limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    _, _, start, end = _range(start_date, end_date)
    rows = db.execute(select(SaleItem.product_id, SaleItem.product_name, SaleItem.sku,
        func.sum(SaleItem.quantity), func.sum(SaleItem.line_total)).join(Sale)
        .where(Sale.created_at >= start, Sale.created_at < end)
        .group_by(SaleItem.product_id, SaleItem.product_name, SaleItem.sku)
        .order_by(func.sum(SaleItem.quantity).desc(), func.sum(SaleItem.line_total).desc())).all()
    # Snapshot identity is intentionally part of the key. A renamed product may
    # have multiple historically correct report rows under the same product ID.
    values = {(r[0], r[1], r[2]): [int(r[3]), Decimal(r[4])] for r in rows}
    returned = db.execute(select(SaleReturnItem.product_id, SaleReturnItem.product_name, SaleReturnItem.sku,
        func.sum(SaleReturnItem.quantity), func.sum(SaleReturnItem.refund_amount)).join(SaleReturn)
        .where(SaleReturn.created_at >= start, SaleReturn.created_at < end)
        .group_by(SaleReturnItem.product_id, SaleReturnItem.product_name, SaleReturnItem.sku)).all()
    for product_id, name, sku, quantity, refund in returned:
        value = values.setdefault((product_id, name, sku), [0, Decimal("0.00")])
        value[0] -= int(quantity); value[1] -= Decimal(refund)
    ordered = sorted(values.items(), key=lambda item: (item[1][0], item[1][1]), reverse=True)[:limit]
    return [TopProduct(product_id=key[0], product_name=key[1], sku=key[2], quantity_sold=v[0], revenue=v[1]) for key, v in ordered]


@router.get("/inventory-status", response_model=InventoryStatus)
def inventory_status(db: Session = Depends(get_db)):
    active, units, _, _ = _inventory(db)
    def products(out: bool):
        condition = Product.current_stock == 0 if out else (Product.current_stock > 0) & (Product.current_stock <= Product.minimum_stock)
        rows = db.scalars(select(Product).where(Product.is_active.is_(True), condition).order_by(Product.current_stock, Product.name)).all()
        return [StockProduct(product_id=p.id, product_name=p.name, sku=p.sku, current_stock=p.current_stock, minimum_stock=p.minimum_stock) for p in rows]
    return InventoryStatus(total_active_products=active, total_units_in_stock=units, low_stock=products(False), out_of_stock=products(True))
