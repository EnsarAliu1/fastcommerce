from sqlalchemy.orm import Session, selectinload
from app import models
from fastapi import HTTPException
from sqlalchemy import update, select
from datetime import datetime, timezone


def get_order_or_404(
    order_id: int,
    user_id: int,
    db: Session
):
    order = db.get(
        models.Order,
        order_id
    )

    if not order or order.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return order


def get_pending_order_for_update(
        order_id: int,
        user_id: int,
        db: Session
):
    statement = (
        select(models.Order)
        .where(
            models.Order.id == order_id,
            models.Order.user_id == user_id
        )
        .with_for_update()
    )

    order = db.scalar(statement)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Order is not pending"
        )

    return order


def expire_order(
        order_id: int,
        db: Session
):
    statement = (
        select(models.Order)
        .where(models.Order.id == order_id)
        .with_for_update()
    )

    order = db.scalar(statement)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Order is not pending"
        )

    reservations = db.query(models.StockReservation).filter(
        models.StockReservation.status == "active",
        models.StockReservation.order_id == order_id
    ).all()

    now = datetime.now(timezone.utc)

    if not reservations or all(
        res.expires_at > now for res in reservations
    ):
        raise HTTPException(
            status_code=409,
            detail="Order is not expired",
        )

    for res in reservations:
        statement = (
            update(models.ProductVariant)
            .where(models.ProductVariant.id == res.variant_id)
            .values(
                stock_quantity=(
                    models.ProductVariant.stock_quantity + res.quantity
                )
            )
        )

        db.execute(statement)
        res.status = "expired"

    order.status = "cancelled"

    db.commit()
    db.refresh(order)
    return order


def mark_order_paid(
        order_id: int,
        user_id: int,
        db: Session
):
    order = get_pending_order_for_update(
        order_id=order_id,
        user_id=user_id,
        db=db
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
        user_id: int,
        db: Session
):
    order = get_pending_order_for_update(
        order_id=order_id,
        user_id=user_id,
        db=db
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
    user_id: int,
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
        .where(models.Order.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()
