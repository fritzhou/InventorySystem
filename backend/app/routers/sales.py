import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Sale, SaleItem
from app.schemas.sale import CheckoutCreate, SaleRead

router = APIRouter(prefix="/api/sales", tags=["sales"])
CENT = Decimal("0.01")


def _receipt_number() -> str:
    return f"SF-{uuid.uuid4().hex[:12].upper()}"


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
        for product_id, quantity in quantities.items():
            product = products[product_id]
            line_total = (product.selling_price * quantity).quantize(CENT)
            result = db.execute(
                update(Product)
                .where(Product.id == product_id, Product.is_active.is_(True), Product.current_stock >= quantity)
                .values(current_stock=Product.current_stock - quantity)
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
        db.commit()
        db.refresh(sale)
        return sale
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Checkout could not be completed. No stock was changed.") from exc
