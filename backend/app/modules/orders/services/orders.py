from sqlalchemy.orm import Session, selectinload
from app import models
from fastapi import HTTPException
from sqlalchemy import update, select


def get_order_or_404(
    order_id: int,
    db: Session
):
    order = db.get(
        models.Order,
        order_id
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return order


def mark_order_paid(
        order_id: int,
        db: Session
):
    order = get_order_or_404(order_id, db)

    if order.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Order is not pending"
        )

    reservations = db.query(models.StockReservation).filter(
        models.StockReservation.order_id == order_id,
        models.StockReservation.status == "active"
    ).all()

    for reservation in reservations:
        reservation.status = "consumed"

    order.status = "paid"

    db.commit()
    db.refresh(order)

    return order


def cancel_order(
        order_id: int,
        db: Session
):
    order = get_order_or_404(
        order_id,
        db
    )

    if order.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Order is not pending"
        )

    reservations = db.query(models.StockReservation).filter(
        models.StockReservation.order_id == order_id,
        models.StockReservation.status == "active"
    ).all()

    for reservation in reservations:
        statement = (
            update(models.ProductVariant)
            .where(
                models.ProductVariant.id == reservation.variant_id
            )
            .values(
                stock_quantity=(
                    reservation.quantity + models.ProductVariant.stock_quantity
                )
            )
            .returning(models.ProductVariant.id)
        )

        db.execute(statement)

        reservation.status = "released"

    order.status = "cancelled"

    db.commit()
    db.refresh(order)

    return order


def get_orders(
    db: Session,
    skip: int,
    limit: int
):
    statement = (
        select(models.Order)
        .options(
            selectinload(models.Order.items)
        )
        .order_by(models.Order.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()
