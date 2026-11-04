from sqlalchemy.orm import Session
from sqlalchemy import select, exists, update
from datetime import datetime, timezone
from app import models
from fastapi import HTTPException


def expire_pending_orders(
        db: Session,
        batch_size: int = 100,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    now = datetime.now(timezone.utc)

    has_expired_reservation = exists().where(
        models.StockReservation.order_id == models.Order.id,
        models.StockReservation.status == "active",
        models.StockReservation.expires_at <= now,
    )

    statement = (
        select(models.Order)
        .where(
            models.Order.status == "pending",
            has_expired_reservation,
        )
        .order_by(models.Order.id)
        .limit(batch_size)
        .with_for_update(
            of=models.Order,
            skip_locked=True
        )
    )

    try:
        orders = db.scalars(statement).all()

        for order in orders:
            _expire_locked_order(order, db, now)

        processed_count = len(orders)

        db.commit()
        return processed_count

    except Exception:
        db.rollback()
        raise


def _expire_locked_order(
    order: models.Order,
    db: Session,
    now: datetime,
) -> None:
    with db.no_autoflush:
        order = db.scalar(
            select(models.Order)
            .where(models.Order.id == order.id)
            .with_for_update(of=models.Order)
            .execution_options(populate_existing=True)
        )
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Order is not pending"
        )

    reservations = db.scalars(
        select(models.StockReservation)
        .where(
            models.StockReservation.order_id == order.id,
            models.StockReservation.status == "active",
        )
        .order_by(models.StockReservation.variant_id, models.StockReservation.id)
        .execution_options(populate_existing=True)
    ).all()

    if not reservations or all(res.expires_at > now for res in reservations):
        raise HTTPException(status_code=409, detail="Order is not expired")

    # Expiration cancels the whole order, returning every active reservation.
    for reservation in reservations:
        db.execute(
            update(models.ProductVariant)
            .where(models.ProductVariant.id == reservation.variant_id)
            .values(stock_quantity=(
                models.ProductVariant.stock_quantity + reservation.quantity
            ))
        )
        reservation.status = "expired"
    order.status = "cancelled"
