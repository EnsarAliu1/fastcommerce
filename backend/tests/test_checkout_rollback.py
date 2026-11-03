from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Cart, CartItem, Order, OrderItem, ProductVariant, StockReservation
from conftest import assert_test_database


def test_insufficient_stock_leaves_no_partial_checkout(client, test_engine, checkout_data):
    with Session(test_engine) as db:
        assert_test_database(db.connection())
        variant_b = ProductVariant(
            product_id=checkout_data["product_id"],
            sku=f"rollback-{uuid4().hex}",
            price=Decimal("25.00"),
            stock_quantity=0,
        )
        extra_item = CartItem(
            cart_id=checkout_data["cart_id"], variant=variant_b, quantity=1
        )
        db.add(extra_item)
        db.flush()
        variant_b_id = variant_b.id
        extra_item_id = extra_item.id
        db.commit()

    try:
        response = client.post(
            f"/carts/{checkout_data['cart_id']}/checkout",
            headers=checkout_data["headers"],
        )

        assert response.status_code == 409, response.text
        assert response.json()["detail"] == "Insufficient stock"

        # Verify committed final state, regardless of cart.items iteration order.
        # This does not prove that A was updated before B failed.
        with Session(test_engine) as db:
            assert db.get(ProductVariant, checkout_data["variant_id"]).stock_quantity == 10
            assert db.get(ProductVariant, variant_b_id).stock_quantity == 0
            cart = db.get(Cart, checkout_data["cart_id"])
            assert cart.status == "active"
            assert {item.variant_id: item.quantity for item in cart.items} == {
                checkout_data["variant_id"]: 2,
                variant_b_id: 1,
            }
            assert db.scalars(select(Order.id).where(
                Order.user_id == checkout_data["user_id"]
            )).all() == []
            variant_ids = [checkout_data["variant_id"], variant_b_id]
            assert db.scalars(select(OrderItem.id).where(
                OrderItem.variant_id.in_(variant_ids)
            )).all() == []
            assert db.scalars(select(StockReservation.id).where(
                StockReservation.variant_id.in_(variant_ids)
            )).all() == []
    finally:
        # Remove B before checkout_data deletes its parent product. Also handle
        # unexpected committed children if the checkout assertions fail.
        with test_engine.begin() as connection:
            assert_test_database(connection)
            connection.execute(delete(StockReservation).where(
                StockReservation.variant_id == variant_b_id
            ))
            connection.execute(delete(OrderItem).where(
                OrderItem.variant_id == variant_b_id
            ))
            connection.execute(delete(CartItem).where(CartItem.id == extra_item_id))
            connection.execute(delete(ProductVariant).where(ProductVariant.id == variant_b_id))
