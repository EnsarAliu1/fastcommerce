from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from time import monotonic, sleep

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Cart, Order, ProductVariant
from conftest import assert_test_database


def test_checkout_waits_for_cart_lock(client, test_engine, checkout_data):
    def do_checkout():
        return client.post(
            f"/carts/{checkout_data['cart_id']}/checkout",
            headers=checkout_data["headers"],
        )

    waiting_query = text("""
        SELECT pid, state, wait_event_type, wait_event, query
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND :holder_pid = ANY(pg_blocking_pids(pid))
    """)

    # The executor must outlive the lock holder: even a failed assertion must
    # release the row lock before executor shutdown waits for the worker.
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(test_engine) as holder:
            try:
                assert_test_database(holder.connection())
                holder_pid = holder.scalar(text("SELECT pg_backend_pid()"))
                cart = holder.scalar(
                    select(Cart)
                    .where(Cart.id == checkout_data["cart_id"])
                    .with_for_update()
                )
                assert cart is not None
                assert cart.status == "active"

                future = executor.submit(do_checkout)

                # Use an independent observer and fresh statistics snapshots
                # for each poll, without ending the holder's transaction.
                with test_engine.connect().execution_options(
                    isolation_level="AUTOCOMMIT"
                ) as observer:
                    deadline = monotonic() + 10
                    blocked = []
                    while monotonic() < deadline:
                        blocked = observer.execute(
                            waiting_query, {"holder_pid": holder_pid}
                        ).mappings().all()
                        if blocked or future.done():
                            break
                        sleep(0.05)

                assert len(blocked) == 1, (
                    "Expected a checkout backend blocked by the holder PID "
                    f"{holder_pid}; observed={blocked}, done={future.done()}"
                )
                waiter = blocked[0]
                assert waiter["pid"] != holder_pid
                assert waiter["state"] == "active"
                assert waiter["wait_event_type"] == "Lock"
                # A later UPDATE could also wait on the row; require evidence
                # that it is the checkout SELECT FOR UPDATE that is blocked.
                query = " ".join(waiter["query"].upper().split())
                assert query.startswith("SELECT "), query
                assert "FROM CART " in query, query
                assert "FOR UPDATE" in query, query
                assert not future.done()
            finally:
                holder.rollback()

        # Never wait for the response while holding the cart lock.
        response = future.result(timeout=10)

    assert response.status_code == 200, response.text
    with Session(test_engine) as db:
        order = db.scalars(
            select(Order).where(Order.user_id == checkout_data["user_id"])
        ).one()
        assert order.id == response.json()["id"]
        assert order.status == "pending"
        assert order.total_amount == Decimal("50.00")
        assert db.get(ProductVariant, checkout_data["variant_id"]).stock_quantity == 8
        assert db.get(Cart, checkout_data["cart_id"]).status == "checked_out"
