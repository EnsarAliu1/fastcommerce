from sqlalchemy.orm import Session
from app import models
from fastapi import HTTPException


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
