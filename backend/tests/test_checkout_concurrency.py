from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cart, Order, OrderItem, ProductVariant, StockReservation


def test_parallel_checkout_creates_only_one_order(client, test_engine, checkout_data):
    # This synchronizes request starts, not arrival at the database row lock.
    # Deterministic lock contention needs a separate controlled-lock test.
    barrier = Barrier(2)

    def do_checkout():
        barrier.wait(timeout=10)
        # The client fixture supplies a separate DB Session for each request.
        return client.post(
            f"/carts/{checkout_data['cart_id']}/checkout",
            headers=checkout_data["headers"],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(do_checkout) for _ in range(2)]
        responses = [future.result() for future in futures]

    assert sorted(response.status_code for response in responses) == [200, 409], [
        (response.status_code, response.text) for response in responses
    ]
    winner = next(response for response in responses if response.status_code == 200)

    # Read committed state in a new session after both requests have finished.
    with Session(test_engine) as db:
        order = db.scalars(select(Order).where(
            Order.user_id == checkout_data["user_id"]
        )).one()
        assert order.id == winner.json()["id"]
        assert order.status == "pending"
        assert order.total_amount == Decimal("50.00")

        item = db.scalars(select(OrderItem).where(
            OrderItem.variant_id == checkout_data["variant_id"]
        )).one()
        assert item.order_id == order.id
        assert item.quantity == 2
        assert item.unit_price == Decimal("25.00")
        assert item.line_total == Decimal("50.00")

        reservation = db.scalars(select(StockReservation).where(
            StockReservation.variant_id == checkout_data["variant_id"]
        )).one()
        assert reservation.order_id == order.id
        assert reservation.status == "active"
        assert reservation.quantity == 2

        assert db.get(ProductVariant, checkout_data["variant_id"]).stock_quantity == 8
        assert db.get(Cart, checkout_data["cart_id"]).status == "checked_out"
