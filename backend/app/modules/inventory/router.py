from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.catalog.schemas.variant import ProductVariantResponse
from app.modules.inventory.schemas.stock import StockAdjustment
from app.modules.inventory.services import stock as stock_service
from app.modules.inventory.schemas.reservation import StockReservationCreate, StockReservationResponse
from app.modules.inventory.services import reservations as reservation_service


router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)

stock_router = APIRouter(
    prefix="/variants",
    tags=["Stock"]
)


@stock_router.post("/{variant_id}/increase-stock", response_model=ProductVariantResponse)
def increase_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db)
):
    return stock_service.increase_stock(variant_id, adjustment, db)


@stock_router.post("/{variant_id}/decrease-stock", response_model=ProductVariantResponse)
def decrease_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db)
):
    return stock_service.decrease_stock(variant_id, adjustment, db)


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
