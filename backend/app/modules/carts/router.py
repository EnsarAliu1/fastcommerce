from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.modules.carts.schemas.cart import CartItemCreate, CartItemQuantityUpdate, CartResponse
from app.modules.orders.schemas.order import OrderResponse

from app.modules.carts.services import carts as carts_service
from app import models
from app.modules.users.dependencies import get_current_user


router = APIRouter(
    prefix="/carts",
    tags=["Carts"]
)


@router.post(
    "/",
    status_code=201,
    response_model=CartResponse
)
def create_cart(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return carts_service.create_cart(
        user_id=current_user.id,
        db=db
    )


@router.get(
    "/{cart_id}",
    response_model=CartResponse
)
def get_cart(
    cart_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return carts_service.get_cart_or_404(
        cart_id=cart_id,
        user_id=current_user.id,
        db=db,
    )


@router.post(
    "/{cart_id}/items",
    status_code=201,
    response_model=CartResponse
)
def add_item(
    cart_id: int,
    data: CartItemCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return carts_service.add_item_to_cart(
        cart_id=cart_id,
        user_id=current_user.id,
        db=db,
        variant_id=data.variant_id,
        quantity=data.quantity
    )


@router.patch(
    "/{cart_id}/items/{item_id}",
    response_model=CartResponse
)
def edit_item(
        cart_id: int,
        item_id: int,
        data: CartItemQuantityUpdate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    return carts_service.update_cart_item_quantity(
        cart_id=cart_id,
        item_id=item_id,
        user_id=current_user.id,
        quantity=data.quantity,
        db=db
    )


@router.delete(
    "/{cart_id}/items/{item_id}",
    status_code=204
)
def delete_item(
    cart_id: int,
    item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    carts_service.remove_cart_item(
        cart_id=cart_id,
        item_id=item_id,
        user_id=current_user.id,
        db=db,
    )


@router.post("/{cart_id}/checkout", response_model=OrderResponse)
def checkout_cart(
    cart_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return carts_service.checkout_cart(
        cart_id=cart_id,
        user_id=current_user.id,
        db=db
    )
