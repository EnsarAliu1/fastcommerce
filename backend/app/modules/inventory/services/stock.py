from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app import models
from app.modules.inventory.schemas.stock import StockAdjustment


def increase_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session
):
    statement = (
        update(models.ProductVariant)
        .where(models.ProductVariant.id == variant_id)
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                + adjustment.quantity
            )
        )
        .returning(models.ProductVariant.id)
    )

    result = db.execute(statement)
    updated_variant_id = result.scalar_one_or_none()

    if updated_variant_id is None:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Product variant not found"
        )

    db.commit()

    variant = db.get(
        models.ProductVariant,
        updated_variant_id
    )

    return variant


def decrease_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session
):
    statement = (
        update(models.ProductVariant)
        .where(
            models.ProductVariant.id == variant_id,
            models.ProductVariant.stock_quantity >= adjustment.quantity
        )
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                - adjustment.quantity
            )
        )
        .returning(models.ProductVariant.id)
    )

    result = db.execute(statement)
    updated_variant_id = result.scalar_one_or_none()

    if updated_variant_id is None:
        variant = db.get(
            models.ProductVariant,
            variant_id
        )

        if variant is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Product variant not found"
            )

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Insufficient stock"
        )

    db.commit()

    variant = db.get(
        models.ProductVariant,
        updated_variant_id
    )

    db.refresh(variant)

    return variant
