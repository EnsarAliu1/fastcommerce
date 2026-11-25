from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProductVariant, StockMovement


def get_stock_movements(
        variant_id: int,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
):
    variant = db.get(ProductVariant, variant_id)

    if variant is None:
        raise HTTPException(
            status_code=404,
            detail="Product variant not found",
        )

    statement = (
        select(StockMovement)
        .where(StockMovement.variant_id == variant_id)
        .order_by(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()
