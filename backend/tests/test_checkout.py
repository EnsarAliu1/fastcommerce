from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Brand, Cart, CartItem, Category, Order, OrderItem,
    Product, ProductVariant, StockReservation,
)
from conftest import assert_test_database


@pytest.fixture
def checkout_data(client, test_engine, user_a_headers):
    me = client.get("/users/me", headers=user_a_headers)
    assert me.status_code == 200, me.text
    user_id = me.json()["id"]
    unique = uuid4().hex

    with Session(test_engine) as db:
        assert_test_database(db.connection())
        category = Category(name="Checkout category", slug=f"category-{unique}")
        brand = Brand(name="Checkout brand", slug=f"brand-{unique}")
        product = Product(
            name="Checkout product", description="Isolated checkout test",
            sku=f"product-{unique}", price=Decimal("25.00"),
            category=category, brand=brand,
        )
        variant = ProductVariant(
            product=product, sku=f"variant-{unique}",
            price=Decimal("25.00"), stock_quantity=10,
        )
        cart = Cart(user_id=user_id, status="active")
        item = CartItem(cart=cart, variant=variant, quantity=2)
        db.add(item)
        db.flush()
        data = {
            "user_id": user_id,
            "category_id": category.id,
            "brand_id": brand.id,
            "product_id": product.id,
            "variant_id": variant.id,
            "cart_id": cart.id,
            "headers": user_a_headers,
        }
        db.commit()

    try:
        yield data
    finally:
        # Find all orders for this unique user, including unexpected duplicates
        # or orders committed before a failing API response/assertion.
        with test_engine.begin() as connection:
            assert_test_database(connection)
            order_ids = select(Order.id).where(Order.user_id == user_id)
            connection.execute(delete(StockReservation).where(
                StockReservation.order_id.in_(order_ids)
            ))
            connection.execute(delete(OrderItem).where(
                OrderItem.order_id.in_(order_ids)
            ))
            connection.execute(delete(Order).where(Order.user_id == user_id))
            connection.execute(delete(CartItem).where(CartItem.cart_id == data["cart_id"]))
            connection.execute(delete(Cart).where(Cart.id == data["cart_id"]))
            connection.execute(delete(ProductVariant).where(ProductVariant.id == data["variant_id"]))
            connection.execute(delete(Product).where(Product.id == data["product_id"]))
            connection.execute(delete(Category).where(Category.id == data["category_id"]))
            connection.execute(delete(Brand).where(Brand.id == data["brand_id"]))
        # user_a_headers/user_data teardown removes the user after this fixture.


@pytest.fixture
def checked_out_order_id(client, checkout_data):
    response = client.post(
        f"/carts/{checkout_data['cart_id']}/checkout",
        headers=checkout_data["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    return response.json()["id"]


def test_checkout_persists_pending_order(test_engine, checkout_data, checked_out_order_id):
    with Session(test_engine) as db:
        order = db.get(Order, checked_out_order_id)
        assert order is not None
        assert order.user_id == checkout_data["user_id"]
        assert order.status == "pending"
        assert order.total_amount == Decimal("50.00")
        assert db.scalars(select(Order.id).where(
            Order.user_id == checkout_data["user_id"]
        )).all() == [checked_out_order_id]


def test_checkout_decreases_stock(test_engine, checkout_data, checked_out_order_id):
    # A new session reads committed stock rather than the setup identity map.
    with Session(test_engine) as db:
        variant = db.get(ProductVariant, checkout_data["variant_id"])
        assert variant.stock_quantity == 8


def test_checkout_persists_order_item(test_engine, checkout_data, checked_out_order_id):
    with Session(test_engine) as db:
        item = db.scalars(select(OrderItem).where(
            OrderItem.order_id == checked_out_order_id
        )).one()
        assert item.variant_id == checkout_data["variant_id"]
        assert item.quantity == 2
        assert item.unit_price == Decimal("25.00")
        assert item.line_total == Decimal("50.00")


def test_checkout_persists_active_reservation(
    test_engine, checkout_data, checked_out_order_id
):
    with Session(test_engine) as db:
        reservation = db.scalars(select(StockReservation).where(
            StockReservation.order_id == checked_out_order_id
        )).one()
        assert reservation.variant_id == checkout_data["variant_id"]
        assert reservation.status == "active"
        assert reservation.quantity == 2
        assert reservation.order_id == checked_out_order_id


def test_checkout_marks_cart_checked_out(test_engine, checkout_data, checked_out_order_id):
    with Session(test_engine) as db:
        cart = db.get(Cart, checkout_data["cart_id"])
        assert cart.status == "checked_out"
        assert cart.user_id == checkout_data["user_id"]


def test_second_checkout_has_no_additional_effects(
    client, test_engine, checkout_data, checked_out_order_id
):
    with Session(test_engine) as db:
        item_id = db.scalars(select(OrderItem.id).where(
            OrderItem.order_id == checked_out_order_id
        )).one()
        reservation_id = db.scalars(select(StockReservation.id).where(
            StockReservation.order_id == checked_out_order_id
        )).one()
        assert db.get(ProductVariant, checkout_data["variant_id"]).stock_quantity == 8

    response = client.post(
        f"/carts/{checkout_data['cart_id']}/checkout",
        headers=checkout_data["headers"],
    )

    assert response.status_code == 409, response.text
    with Session(test_engine) as db:
        orders = db.scalars(select(Order).where(
            Order.user_id == checkout_data["user_id"]
        )).all()
        assert [order.id for order in orders] == [checked_out_order_id]
        order = orders[0]
        assert order.status == "pending"
        assert order.total_amount == Decimal("50.00")
        assert [item.id for item in order.items] == [item_id]
        assert [reservation.id for reservation in order.reservations] == [reservation_id]
        assert order.items[0].quantity == 2
        assert order.reservations[0].quantity == 2
        assert order.reservations[0].status == "active"
        assert db.get(ProductVariant, checkout_data["variant_id"]).stock_quantity == 8
        assert db.get(Cart, checkout_data["cart_id"]).status == "checked_out"
