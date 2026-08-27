import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Product
from app.schemas.product import ProductCreate, ProductLookupRead, ProductRead, ProductUpdate
from app.services.product_lookup import ProviderUnavailableError, ProductLookupProvider, get_product_lookup_provider

router = APIRouter(prefix="/api/products", tags=["products"])


def _commit_product(db: Session, product: Product) -> Product:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="SKU or barcode already exists.") from exc
    db.refresh(product)
    return product


def _require_category(db: Session, category_id: uuid.UUID) -> None:
    if db.get(Category, category_id) is None:
        raise HTTPException(status_code=422, detail="Category does not exist.")


@router.get("", response_model=list[ProductRead])
def list_products(
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Product]:
    statement = select(Product)
    if active_only:
        statement = statement.where(Product.is_active.is_(True))
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Product.name.ilike(term), Product.sku.ilike(term), Product.barcode.ilike(term)))
    return list(db.scalars(statement.order_by(Product.name).offset(offset).limit(limit)))


@router.get("/barcode/{barcode}", response_model=ProductRead)
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)) -> Product:
    product = db.scalar(select(Product).where(Product.barcode == barcode))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.get("/barcode/{barcode}/lookup", response_model=ProductLookupRead)
def lookup_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    provider: ProductLookupProvider = Depends(get_product_lookup_provider),
) -> ProductLookupRead:
    product = db.scalar(select(Product).where(Product.barcode == barcode))
    if product is not None:
        return ProductLookupRead(found=True, source="stockflow", product=ProductRead.model_validate(product))
    try:
        external_product = provider.lookup(barcode)
    except ProviderUnavailableError:
        return ProductLookupRead(found=False, source="none", reason="provider_unavailable")
    if external_product is None:
        return ProductLookupRead(found=False, source="none", reason="not_found")
    return ProductLookupRead(found=True, source=provider.name, external_product=external_product)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    _require_category(db, payload.category_id)
    product = Product(**payload.model_dump())
    db.add(product)
    return _commit_product(db, product)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and changes["category_id"] is not None:
        _require_category(db, changes["category_id"])
    for field, value in changes.items():
        setattr(product, field, value)
    return _commit_product(db, product)


@router.delete("/{product_id}", response_model=ProductRead)
def deactivate_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    product.is_active = False
    return _commit_product(db, product)
