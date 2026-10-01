from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.schemas.reservation import StockReservationCreate


router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)


@router.post("/{variant_id}", status_code=201)
def create_reservation(
    variant_id: int,
    data: StockReservationCreate,
    db: Session = Depends(get_db)
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

        variant = db.get(models.ProductVariant, variant_id)

        if variant is None:
            raise HTTPException(
                status_code=404,
                detail="Product varian not found"
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


@router.post("/{reservation_id}/release")
def reservation_release(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    reservation = db.query(models.StockReservation).filter(
        models.StockReservation.id == reservation_id
    ).first()

    if not reservation:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
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


@router.post("/{reservation_id}/consume")
def reservation_consume(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    reservation = db.query(models.StockReservation).filter(
        models.StockReservation.id == reservation_id
    ).first()

    if not reservation:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
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
