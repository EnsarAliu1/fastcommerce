from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.catalog.schemas.variant import ProductVariantResponse
from app.modules.inventory.schemas.stock import StockAdjustment
from app.modules.inventory.services import stock as stock_service
from app.modules.inventory.schemas.reservation import StockReservationCreate, StockReservationResponse
from app.modules.inventory.services import reservations as reservation_service
from app.modules.users.dependencies import get_current_admin

from app.models import User

from app.modules.inventory.schemas.stock_movement import StockMovementResponse
from app.modules.inventory.services import stock_movements


router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"],
    dependencies=[Depends(get_current_admin)]
)

stock_router = APIRouter(
    prefix="/variants",
    tags=["Stock"],
    dependencies=[Depends(get_current_admin)]
)


@stock_router.post("/{variant_id}/increase-stock", response_model=ProductVariantResponse)
def increase_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return stock_service.increase_stock(variant_id, adjustment, db, admin_id=current_admin.id)


@stock_router.post("/{variant_id}/decrease-stock", response_model=ProductVariantResponse)
def decrease_stock(
    variant_id: int,
    adjustment: StockAdjustment,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return stock_service.decrease_stock(variant_id, adjustment, db, admin_id=current_admin.id)


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


@stock_router.get(
    "/{variant_id}/stock-movements",
    response_model=list[StockMovementResponse],
)
def get_stock_movements(
    variant_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return stock_movements.get_stock_movements(
        variant_id,
        db,
        skip=skip,
        limit=limit,
    )
