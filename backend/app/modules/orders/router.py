from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.orders.schemas.order import OrderResponse
from app.modules.orders.services import orders as orders_service
from app import models
from app.modules.users.dependencies import get_current_user

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return orders_service.get_order_or_404(
        order_id=order_id,
        user_id=current_user.id,
        db=db
    )


@router.post(
    "/{order_id}/pay",
    response_model=OrderResponse
)
def pay_order(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return orders_service.mark_order_paid(
        order_id=order_id,
        user_id=current_user.id,
        db=db
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse
)
def cancel_order(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return orders_service.cancel_order(
        order_id=order_id,
        user_id=current_user.id,
        db=db
    )


@router.get("/", response_model=list[OrderResponse])
def get_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100)
):
    return orders_service.get_orders(
        user_id=current_user.id,
        db=db,
        skip=skip,
        limit=limit
    )
