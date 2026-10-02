from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.reservation import StockReservationCreate, StockReservationResponse
from app.services import reservations as reservation_service


router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)


@router.post("/{variant_id}", status_code=201, response_model=StockReservationResponse)
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


@router.post("/{reservation_id}/release", response_model=StockReservationResponse)
def reservation_release(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.release_reservation(
        reservation_id,
        db
    )


@router.post("/{reservation_id}/consume", response_model=StockReservationResponse)
def reservation_consume(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.consume_reservation(
        reservation_id,
        db
    )


@router.post("/{reservation_id}/expire", response_model=StockReservationResponse)
def reservation_expire(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.expire_reservation(
        reservation_id,
        db
    )


@router.get(
    "/",
    response_model=list[StockReservationResponse]
)
def get_reservations(
    db: Session = Depends(get_db)
):
    return reservation_service.get_reservations(
        db
    )


@router.get(
    "/{reservation_id}",
    response_model=StockReservationResponse
)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    return reservation_service.get_reservation(
        reservation_id,
        db
    )
