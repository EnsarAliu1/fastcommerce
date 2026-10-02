from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


def create_cart(
        db: Session
):
    cart = models.Cart(status="active")
    db.add(cart)
    db.commit()
    db.refresh(cart)

    return cart


def get_cart_or_404(
        cart_id: int,
        db: Session
):
    cart = db.get(
        models.Cart,
        cart_id
    )

    if not cart:
        raise HTTPException(
            status_code=404,
            detail="Cart not found"
        )

    return cart


def add_item_to_cart(
        cart_id: int,
        db: Session,
        variant_id: int,
        quantity: int
):
    cart = get_cart_or_404(cart_id, db)

    if cart.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Cart is not active"
        )

    variant = db.get(
        models.ProductVariant,
        variant_id
    )

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )

    existing_variant = next(
        (item for item in cart.items if item.variant_id == variant_id),
        None
    )

    if existing_variant:
        existing_variant.quantity += quantity

    # nese jo krijo cart item
    if not existing_variant:
        cart_item = models.CartItem(
            cart_id=cart.id,
            variant_id=variant_id,
            quantity=quantity
        )
        db.add(cart_item)

    db.commit()
    db.refresh(cart)

    return cart
