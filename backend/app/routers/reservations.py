from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.reservation import StockReservationCreate
from app.services import reservations as reservation_service


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
    return reservation_service.create_reservation(
        variant_id,
        data,
        db
    )


@router.post("/{reservation_id}/release")
def reservation_release(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.release_reservation(
        reservation_id,
        db
    )


@router.post("/{reservation_id}/consume")
def reservation_consume(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.consume_reservation(
        reservation_id,
        db
    )


@router.post("/{reservation_id}/expire")
def reservation_expire(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.expire_reservation(
        reservation_id,
        db
    )
