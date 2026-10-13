from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update

from datetime import datetime, timedelta, timezone

from app import models

from decimal import Decimal


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

    current_quantity = (
        existing_variant.quantity
        if existing_variant
        else 0
    )

    requested_total = current_quantity + quantity

    if requested_total > variant.stock_quantity:
        raise HTTPException(
            status_code=409,
            detail="Insufficient stock"
        )

    if existing_variant:
        existing_variant.quantity += quantity

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


def update_cart_item_quantity(
        cart_id: int,
        item_id: int,
        quantity: int,
        db: Session
):
    cart = get_cart_or_404(cart_id, db)

    if cart.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Cart is not active"
        )

    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.cart_id == cart_id
    ).first()
    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail="Cart item not found"
        )
    variant = db.get(
        models.ProductVariant,
        cart_item.variant_id
    )
    if quantity > variant.stock_quantity:
        raise HTTPException(
            status_code=409,
            detail="Insufficient stock"
        )
    cart_item.quantity = quantity

    db.commit()
    db.refresh(cart)

    return cart


def remove_cart_item(
        cart_id: int,
        item_id: int,
        db: Session
):
    cart = get_cart_or_404(cart_id, db)

    if cart.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Cart item is not active"
        )

    cart_item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.cart_id == cart_id
    ).first()

    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail="Cart is not active"
        )

    db.delete(cart_item)
    db.commit()
    db.refresh(cart)

    return cart


def checkout_cart(
    cart_id: int,
    db: Session
):
    cart = get_cart_or_404(
        cart_id,
        db
    )

    if cart.status != "active":
        raise HTTPException(
            status_code=409,
            detail="Cart is not active"
        )

    if not cart.items:
        raise HTTPException(
            status_code=409,
            detail="Cart is empty"
        )

    order = models.Order(
        status="pending",
        total_amount=Decimal("0.00")
    )

    db.add(order)
    db.flush()

    total_amount = Decimal("0.00")

    for item in cart.items:
        variant = db.get(
            models.ProductVariant,
            item.variant_id
        )

        if not variant:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Product variant not found"
            )

        statement = (
            update(models.ProductVariant)
            .where(
                models.ProductVariant.id == item.variant_id,
                models.ProductVariant.stock_quantity >= item.quantity
            )
            .values(
                stock_quantity=(
                    models.ProductVariant.stock_quantity
                    - item.quantity
                )
            )
            .returning(models.ProductVariant.id)
        )

        result = db.execute(statement)
        updated_variant_id = result.scalar_one_or_none()

        if updated_variant_id is None:
            db.rollback()

            raise HTTPException(
                status_code=409,
                detail="Insufficient stock"
            )

        line_total = variant.price * item.quantity

        order_item = models.OrderItem(
            order_id=order.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=variant.price,
            line_total=line_total
        )

        db.add(order_item)

        reservation = models.StockReservation(
            variant_id=item.variant_id,
            quantity=item.quantity,
            status="active",
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=15)
            ),
            order_id=order.id
        )

        db.add(reservation)

        total_amount += line_total

    order.total_amount = total_amount
    cart.status = "checked_out"

    db.commit()
    db.refresh(order)

    return order
