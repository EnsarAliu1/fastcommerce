from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import models
from app.modules.inventory.schemas.stock import StockAdjustment


def _adjust_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session,
    *,
    admin_id: int,
    decrease: bool,
):
    delta = -adjustment.quantity if decrease else adjustment.quantity

    try:
        if admin_id is None or admin_id <= 0:
            raise ValueError("Manual stock adjustments require an admin_id")

        statement = update(models.ProductVariant).where(
            models.ProductVariant.id == variant_id
        )

        if decrease:
            statement = statement.where(
                models.ProductVariant.stock_quantity >= adjustment.quantity
            )

        statement = (
            statement
            .values(
                stock_quantity=models.ProductVariant.stock_quantity + delta
            )
            .returning(
                models.ProductVariant.id,
                models.ProductVariant.stock_quantity,
            )
            .execution_options(synchronize_session=False)
        )

        result = db.execute(statement).one_or_none()

        if result is None:
            existing_id = db.scalar(
                select(models.ProductVariant.id).where(
                    models.ProductVariant.id == variant_id
                )
            )

            if existing_id is None:
                raise HTTPException(
                    status_code=404,
                    detail="Product variant not found",
                )

            raise HTTPException(
                status_code=409,
                detail="Insufficient stock",
            )

        updated_id, stock_after = result

        movement = models.StockMovement(
            variant_id=updated_id,
            admin_id=admin_id,
            movement_type=(
                "manual_decrease" if decrease else "manual_increase"
            ),
            quantity_delta=delta,
            stock_before=stock_after - delta,
            stock_after=stock_after,
            reason=adjustment.reason,
        )
        db.add(movement)

        # UPDATE and INSERT are committed together.
        db.commit()

    except Exception:
        db.rollback()
        raise

    variant = db.get(models.ProductVariant, updated_id)
    db.refresh(variant)
    return variant


def increase_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session,
    *,
    admin_id: int,
):
    return _adjust_stock(
        variant_id,
        adjustment,
        db,
        admin_id=admin_id,
        decrease=False,
    )


def decrease_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session,
    *,
    admin_id: int,
):
    return _adjust_stock(
        variant_id,
        adjustment,
        db,
        admin_id=admin_id,
        decrease=True,
    )
