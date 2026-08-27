import secrets
import uuid
from datetime import date, datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import admin_role
from app.models.user import User
from app.audit import record_audit
from app.models import Expense, ExpenseCategory, ExpenseStatus
from app.routers.reports import _timezone
from app.schemas.expense import (ExpenseCategoryCreate, ExpenseCategoryRead, ExpenseCategoryUpdate,
    ExpenseCreate, ExpensePage, ExpenseRead, ExpenseUpdate, ExpenseVoid)

router = APIRouter(prefix="/api", tags=["expenses"], dependencies=[Depends(admin_role)])


def _category(db: Session, category_id: uuid.UUID, *, active=False):
    category = db.get(ExpenseCategory, category_id)
    if category is None:
        raise HTTPException(404, "Expense category not found")
    if active and not category.is_active:
        raise HTTPException(422, "Expense category is inactive")
    return category


def _commit(db: Session, duplicate="An expense category with this name already exists"):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, duplicate) from exc


@router.get("/expense-categories", response_model=list[ExpenseCategoryRead])
def categories(active_only: bool = False, db: Session = Depends(get_db)):
    query = select(ExpenseCategory)
    if active_only:
        query = query.where(ExpenseCategory.is_active.is_(True))
    return list(db.scalars(query.order_by(ExpenseCategory.name)))


@router.post("/expense-categories", response_model=ExpenseCategoryRead, status_code=201)
def create_category(payload: ExpenseCategoryCreate, db: Session = Depends(get_db)):
    if db.scalar(select(ExpenseCategory.id).where(func.lower(ExpenseCategory.name) == payload.name.lower())):
        raise HTTPException(409, "An expense category with this name already exists")
    item = ExpenseCategory(name=payload.name, description=payload.description)
    db.add(item); _commit(db); db.refresh(item)
    return item


@router.patch("/expense-categories/{category_id}", response_model=ExpenseCategoryRead)
def update_category(category_id: uuid.UUID, payload: ExpenseCategoryUpdate, db: Session = Depends(get_db)):
    item = _category(db, category_id)
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and db.scalar(select(ExpenseCategory.id).where(func.lower(ExpenseCategory.name) == values["name"].lower(), ExpenseCategory.id != item.id)):
        raise HTTPException(409, "An expense category with this name already exists")
    for key, value in values.items(): setattr(item, key, value)
    _commit(db); db.refresh(item)
    return item


@router.delete("/expense-categories/{category_id}", response_model=ExpenseCategoryRead)
def deactivate_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    item = _category(db, category_id); item.is_active = False
    db.commit(); db.refresh(item)
    return item


def _number() -> str:
    today = datetime.now(_timezone()).strftime("%Y%m%d")
    return f"EXP-{today}-{secrets.token_hex(2).upper()}"


@router.post("/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), actor: User = Depends(admin_role)):
    category = _category(db, payload.category_id, active=True)
    item = Expense(**payload.model_dump(), category_name=category.name, expense_number=_number(), created_by_user_id=actor.id)
    db.add(item); db.flush(); record_audit(db, actor, "EXPENSE_CREATED", "EXPENSE", item.id); _commit(db, "Could not generate a unique expense number; please retry"); db.refresh(item)
    return item


@router.get("/expenses", response_model=ExpensePage)
def expenses(search: str = "", category_id: uuid.UUID | None = None, status: ExpenseStatus | None = None,
             start_date: date | None = None, end_date: date | None = None,
             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="From date cannot be after To date")
    filters = []
    if search.strip():
        term = f"%{search.strip().lower()}%"
        filters.append(or_(func.lower(Expense.expense_number).like(term), func.lower(Expense.description).like(term)))
    if category_id: filters.append(Expense.category_id == category_id)
    if status: filters.append(Expense.status == status)
    if start_date: filters.append(Expense.expense_date >= start_date)
    if end_date: filters.append(Expense.expense_date <= end_date)
    total = db.scalar(select(func.count(Expense.id)).where(*filters)) or 0
    items = list(db.scalars(select(Expense).where(*filters).order_by(Expense.expense_date.desc(), Expense.created_at.desc()).offset((page-1)*page_size).limit(page_size)))
    return ExpensePage(items=items, total=total, page=page, page_size=page_size, pages=ceil(total/page_size) if total else 0)


@router.get("/expenses/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: uuid.UUID, db: Session = Depends(get_db)):
    item = db.get(Expense, expense_id)
    if not item: raise HTTPException(404, "Expense not found")
    return item


@router.patch("/expenses/{expense_id}", response_model=ExpenseRead)
def update_expense(expense_id: uuid.UUID, payload: ExpenseUpdate, db: Session = Depends(get_db), actor: User = Depends(admin_role)):
    item = get_expense(expense_id, db)
    if item.status == ExpenseStatus.VOIDED: raise HTTPException(409, "Voided expenses cannot be edited")
    values = payload.model_dump(exclude_unset=True)
    if "category_id" in values and values["category_id"] != item.category_id:
        # An expense may retain its historical category after that category is
        # deactivated, but it cannot be moved to an inactive category.
        category = _category(db, values["category_id"], active=True)
        item.category_name = category.name
    for key, value in values.items(): setattr(item, key, value)
    item.updated_by_user_id = actor.id; record_audit(db, actor, "EXPENSE_UPDATED", "EXPENSE", item.id); db.commit(); db.refresh(item)
    return item


@router.post("/expenses/{expense_id}/void", response_model=ExpenseRead)
def void_expense(expense_id: uuid.UUID, payload: ExpenseVoid, db: Session = Depends(get_db), actor: User = Depends(admin_role)):
    # A conditional transition is atomic on both PostgreSQL and SQLite. It
    # prevents two stale readers from each reporting a successful first void.
    result = db.execute(update(Expense).where(
        Expense.id == expense_id, Expense.status == ExpenseStatus.ACTIVE,
    ).values(status=ExpenseStatus.VOIDED, void_reason=payload.reason, voided_at=datetime.now(timezone.utc), voided_by_user_id=actor.id, updated_by_user_id=actor.id))
    if result.rowcount == 0:
        db.rollback()
        if db.get(Expense, expense_id) is None:
            raise HTTPException(404, "Expense not found")
        raise HTTPException(409, "Expense is already voided")
    record_audit(db, actor, "EXPENSE_VOIDED", "EXPENSE", expense_id); db.commit()
    return db.get(Expense, expense_id)
