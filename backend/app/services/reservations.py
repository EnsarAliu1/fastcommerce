from sqlalchemy.orm import Session
from sqlalchemy import update

from datetime import datetime, timezone, timedelta

from app.schemas.reservation import StockReservationCreate

from fastapi import HTTPException

from app import models


def get_reservation_or_404(
    reservation_id: int,
    db: Session
):
    reservation = db.get(
        models.StockReservation,
        reservation_id
    )

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    return reservation


def release_reservation(
        reservation_id: int,
        db: Session
):
    reservation = get_reservation_or_404(
        reservation_id,
        db
    )

    if reservation.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Reservation is not active"
        )

    statement = (
        update(models.ProductVariant)
        .where(
            models.ProductVariant.id == reservation.variant_id
        )
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                + reservation.quantity
            )
        )
    )

    db.execute(statement)

    reservation.status = "released"

    db.commit()
    db.refresh(reservation)

    return reservation


def create_reservation(
    variant_id: int,
    data: StockReservationCreate,
    db: Session
):
    statement = (
        update(models.ProductVariant)
        .where(
            models.ProductVariant.id == variant_id,
            models.ProductVariant.stock_quantity >= data.quantity
        )
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                - data.quantity
            )
        )
        .returning(models.ProductVariant.id)
    )

    result = db.execute(statement)
    updated_variant_id = result.scalar_one_or_none()

    if updated_variant_id is None:
        db.rollback()

        variant = db.get(
            models.ProductVariant,
            variant_id
        )

        if variant is None:
            raise HTTPException(
                status_code=404,
                detail="Product variant not found"
            )

        raise HTTPException(
            status_code=409,
            detail="Insufficient stock"
        )

    reservation = models.StockReservation(
        variant_id=variant_id,
        quantity=data.quantity,
        status="active",
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(minutes=15)
        )
    )

    db.add(reservation)

    db.commit()
    db.refresh(reservation)

    return reservation


def consume_reservation(
    reservation_id: int,
    db: Session
):
    reservation = get_reservation_or_404(
        reservation_id,
        db
    )

    if reservation.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Reservation is not active"
        )

    reservation.status = "consumed"

    db.commit()
    db.refresh(reservation)

    return reservation


def expire_reservation(
    reservation_id: int,
    db: Session
):
    reservation = get_reservation_or_404(
        reservation_id,
        db
    )

    if reservation.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Reservation is not active"
        )

    if reservation.expires_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=409,
            detail="Reservation has not expired yet"
        )

    statement = (
        update(models.ProductVariant)
        .where(
            models.ProductVariant.id == reservation.variant_id
        )
        .values(
            stock_quantity=(
                models.ProductVariant.stock_quantity
                + reservation.quantity
            )
        )
    )

    db.execute(statement)

    reservation.status = "expired"

    db.commit()
    db.refresh(reservation)

    return reservation


def get_reservations(
        db: Session
):
    return db.query(
        models.StockReservation
    ).all()


def get_reservation(
        reservation_id: int,
        db: Session
):
    return get_reservation_or_404(
        reservation_id,
        db
    )
