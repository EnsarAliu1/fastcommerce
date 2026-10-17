from fastapi import APIRouter, Depends
from app.modules.users.dependencies import get_current_admin
from app.modules.orders.schemas.order import OrderResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.modules.orders.services import orders as orders_service

router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Orders"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("/{order_id}/expire", response_model=OrderResponse)
def expire_orders(
    order_id: int,
    db: Session = Depends(get_db),
):
    return orders_service.expire_order(
        order_id=order_id,
        db=db,
    )
