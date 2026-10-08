from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.cart import CartItemCreate, CartItemQuantityUpdate, CartResponse
from app.schemas.order import OrderResponse

from app.services import carts as carts_service


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
    db: Session = Depends(get_db)
):
    return carts_service.create_cart(db)


@router.get(
    "/{cart_id}",
    response_model=CartResponse
)
def get_cart(
    cart_id: int,
    db: Session = Depends(get_db)
):
    return carts_service.get_cart_or_404(cart_id, db)


@router.post(
    "/{cart_id}/items",
    status_code=201,
    response_model=CartResponse
)
def add_item(
    cart_id: int,
    data: CartItemCreate,
    db: Session = Depends(get_db)
):
    return carts_service.add_item_to_cart(
        cart_id=cart_id,
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
        db: Session = Depends(get_db)
):
    return carts_service.update_cart_item_quantity(
        cart_id,
        item_id,
        data.quantity,
        db
    )


@router.delete(
    "/{cart_id}/items/{item_id}",
    status_code=204
)
def delete_item(
    cart_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    carts_service.remove_cart_item(
        cart_id,
        item_id,
        db
    )


@router.post("/{cart_id}/checkout", response_model=OrderResponse)
def checkout_cart(
    cart_id: int,
    db: Session = Depends(get_db)
):
    return carts_service.checkout_cart(
        cart_id,
        db
    )
