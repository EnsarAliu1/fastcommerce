from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cart, Order, OrderItem, ProductVariant, StockReservation
from conftest import assert_test_database


def test_checkout_rolls_back_changes_when_commit_fails(
    client, test_engine, checkout_data, monkeypatch
):
    observed_order_ids = []
    failure = RuntimeError("Injected checkout failure before COMMIT")

    def fail_before_commit(session):
        assert session.get_bind() is test_engine
        connection = session.connection()
        assert_test_database(connection)

        # Read SQL directly, without ORM identity-map values or autoflush:
        # checkout's stock UPDATE must already have executed at this point.
        stock = connection.scalar(select(ProductVariant.stock_quantity).where(
            ProductVariant.id == checkout_data["variant_id"]
        ))
        assert stock == 8
        order_id = connection.execute(select(Order.id).where(
            Order.user_id == checkout_data["user_id"]
        )).scalar_one()

        # Perform the flush that commit would normally perform, so the pending
        # item, reservation and cart changes also reach PostgreSQL before failure.
        session.flush()
        assert connection.scalar(select(Cart.status).where(
            Cart.id == checkout_data["cart_id"]
        )) == "checked_out"
        assert connection.scalar(select(Order.total_amount).where(
            Order.id == order_id
        )) == Decimal("50.00")
        connection.execute(select(OrderItem.id).where(
            OrderItem.order_id == order_id
        )).scalar_one()
        connection.execute(select(StockReservation.id).where(
            StockReservation.order_id == order_id
        )).scalar_one()

        observed_order_ids.append(order_id)
        raise failure

    # Setup has finished. Restore commit immediately after this one request,
    # including on failure, before verification or fixture cleanup runs.
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_before_commit)
        with pytest.raises(RuntimeError) as caught:
            client.post(
                f"/carts/{checkout_data['cart_id']}/checkout",
                headers=checkout_data["headers"],
            )

    assert caught.value is failure
    assert len(observed_order_ids) == 1

    # The request's session lifecycle must roll back; the test does not manually
    # roll back that session. A new session checks what was actually persisted.
    with Session(test_engine) as db:
        assert db.get(ProductVariant, checkout_data["variant_id"]).stock_quantity == 10
        assert db.get(Cart, checkout_data["cart_id"]).status == "active"
        assert db.get(Order, observed_order_ids[0]) is None
        assert db.scalars(select(Order.id).where(
            Order.user_id == checkout_data["user_id"]
        )).all() == []
        assert db.scalars(select(OrderItem.id).where(
            OrderItem.variant_id == checkout_data["variant_id"]
        )).all() == []
        assert db.scalars(select(StockReservation.id).where(
            StockReservation.variant_id == checkout_data["variant_id"]
        )).all() == []
