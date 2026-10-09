from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.order import OrderResponse
from app.services import orders as orders_service

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.get(
    "/{order_id}",
    response_model=OrderResponse
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    return orders_service.get_order_or_404(
        order_id,
        db
    )


@router.post(
    "/{order_id}/pay",
    response_model=OrderResponse
)
def pay_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    return orders_service.mark_order_paid(
        order_id,
        db
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    return orders_service.cancel_order(
        order_id,
        db
    )


@router.get("/", response_model=list[OrderResponse])
def get_orders(
    db: Session = Depends(get_db),
        skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    return orders_service.get_orders(
        db,
        skip,
        limit
    )
