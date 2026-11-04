from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Order, ProductVariant, StockReservation
from app.modules.orders.services import expiration, orders


@pytest.fixture
def batch_data(test_engine, checkout_data):
    # The service is global. Lock other users' existing orders so SKIP LOCKED
    # excludes shared test data without modifying or deleting it.
    with Session(test_engine) as guard:
        guard.scalars(select(Order).where(
            (Order.user_id != checkout_data["user_id"]) | Order.user_id.is_(None)
        ).with_for_update(of=Order)).all()
        try:
            yield checkout_data
        finally:
            guard.rollback()
    # checkout_data removes our reservations/orders before deleting the user.


@pytest.fixture
def make_order(test_engine, batch_data):
    def create(*, status="pending", expired=True, reservation_status="active"):
        with Session(test_engine) as db:
            order = Order(
                user_id=batch_data["user_id"], status=status,
                total_amount=Decimal("50.00"),
            )
            reservation = StockReservation(
                order=order, variant_id=batch_data["variant_id"], quantity=2,
                status=reservation_status,
                expires_at=datetime.now(timezone.utc) + timedelta(
                    days=-1 if expired else 1
                ),
            )
            db.add(reservation)
            variant = db.get(ProductVariant, batch_data["variant_id"])
            variant.stock_quantity -= 2
            db.flush()
            ids = (order.id, reservation.id)
            db.commit()
            return ids
    return create


def run_batch(engine, batch_size=100):
    with Session(engine) as db:
        return expiration.expire_pending_orders(db, batch_size)


def read_state(engine, data):
    with Session(engine) as db:
        return {
            "stock": db.get(ProductVariant, data["variant_id"]).stock_quantity,
            "orders": dict(db.execute(select(Order.id, Order.status).where(
                Order.user_id == data["user_id"]
            )).all()),
            "reservations": dict(db.execute(select(
                StockReservation.id, StockReservation.status
            ).where(StockReservation.variant_id == data["variant_id"])).all()),
        }


def test_no_expired_orders(test_engine, batch_data, make_order):
    make_order(expired=False)
    before = read_state(test_engine, batch_data)
    assert run_batch(test_engine) == 0
    assert read_state(test_engine, batch_data) == before


def test_expired_order_is_cancelled(test_engine, batch_data, make_order):
    order_id, _ = make_order()
    assert run_batch(test_engine) == 1
    assert read_state(test_engine, batch_data)["orders"] == {order_id: "cancelled"}


def test_expired_reservation_returns_stock(test_engine, batch_data, make_order):
    _, reservation_id = make_order()
    assert read_state(test_engine, batch_data)["stock"] == 8
    assert run_batch(test_engine) == 1
    state = read_state(test_engine, batch_data)
    assert state["stock"] == 10
    assert state["reservations"] == {reservation_id: "expired"}


def test_second_call_does_not_return_stock_again(test_engine, batch_data, make_order):
    make_order()
    assert run_batch(test_engine) == 1
    before = read_state(test_engine, batch_data)
    assert run_batch(test_engine) == 0
    assert read_state(test_engine, batch_data) == before
    assert before["stock"] == 10


def test_batch_size_limits_orders(test_engine, batch_data, make_order):
    created = [make_order() for _ in range(3)]
    assert run_batch(test_engine, batch_size=2) == 2
    state = read_state(test_engine, batch_data)
    assert state["orders"] == {
        created[0][0]: "cancelled", created[1][0]: "cancelled",
        created[2][0]: "pending",
    }
    assert state["reservations"] == {
        created[0][1]: "expired", created[1][1]: "expired",
        created[2][1]: "active",
    }
    assert state["stock"] == 8


def test_paid_order_is_untouched(test_engine, batch_data, make_order):
    # Even an old active reservation must not expire a paid order.
    make_order(status="paid")
    before = read_state(test_engine, batch_data)
    assert run_batch(test_engine) == 0
    assert read_state(test_engine, batch_data) == before


def test_failure_rolls_back_entire_batch(test_engine, batch_data, make_order, monkeypatch):
    created = [make_order() for _ in range(3)]
    before = read_state(test_engine, batch_data)
    original = expiration._expire_locked_order
    processed = []
    failure = RuntimeError("Injected batch expiration failure")

    def fail_on_second(order, db, now):
        original(order, db, now)
        db.flush()
        processed.append(order.id)
        if len(processed) == 2:
            # Prove changes reached SQL before raising, not only ORM memory.
            connection = db.connection()
            assert connection.scalar(select(ProductVariant.stock_quantity).where(
                ProductVariant.id == batch_data["variant_id"]
            )) == 8
            assert connection.scalar(select(Order.status).where(
                Order.id == created[0][0]
            )) == "cancelled"
            raise failure

    with monkeypatch.context() as patch:
        patch.setattr(expiration, "_expire_locked_order", fail_on_second)
        with Session(test_engine) as db:
            with pytest.raises(RuntimeError) as caught:
                expiration.expire_pending_orders(db)
            assert caught.value is failure
            # Check rollback happened in the service, before session.close().
            assert not db.in_transaction()
            assert read_state(test_engine, batch_data) == before
    assert processed == [created[0][0], created[1][0]]


@pytest.mark.parametrize("batch_size", [0, -1])
def test_invalid_batch_size(test_engine, batch_data, batch_size):
    with pytest.raises(ValueError, match="batch_size must be greater than zero"):
        run_batch(test_engine, batch_size)


def test_locked_order_is_skipped(test_engine, batch_data, make_order):
    first, second = make_order(), make_order()
    with Session(test_engine) as holder:
        try:
            holder.scalar(select(Order).where(Order.id == first[0]).with_for_update())
            with Session(test_engine) as worker:
                # A regression to waiting fails quickly instead of hanging.
                worker.execute(text("SET LOCAL lock_timeout = '2s'"))
                assert expiration.expire_pending_orders(worker, batch_size=1) == 1
            state = read_state(test_engine, batch_data)
            assert state["orders"] == {first[0]: "pending", second[0]: "cancelled"}
            assert state["stock"] == 8
        finally:
            holder.rollback()
    assert run_batch(test_engine) == 1
    assert read_state(test_engine, batch_data)["stock"] == 10


def test_single_order_expiration_still_works(test_engine, batch_data, make_order):
    order_id, reservation_id = make_order()
    with Session(test_engine) as db:
        assert orders.expire_order(order_id, db).status == "cancelled"
    assert read_state(test_engine, batch_data) == {
        "stock": 10, "orders": {order_id: "cancelled"},
        "reservations": {reservation_id: "expired"},
    }


@pytest.mark.parametrize("status,expired,detail", [
    ("paid", True, "Order is not pending"),
    ("pending", False, "Order is not expired"),
])
def test_single_order_validation_is_preserved(
    test_engine, batch_data, make_order, status, expired, detail
):
    order_id, _ = make_order(status=status, expired=expired)
    before = read_state(test_engine, batch_data)
    with Session(test_engine) as db:
        with pytest.raises(HTTPException) as caught:
            orders.expire_order(order_id, db)
        assert caught.value.status_code == 409
        assert caught.value.detail == detail
        assert not db.in_transaction()
    assert read_state(test_engine, batch_data) == before


def test_expiration_returns_all_active_reservations(test_engine, batch_data, make_order):
    order_id, reservation_id = make_order()
    with Session(test_engine) as db:
        extra = StockReservation(
            order_id=order_id, variant_id=batch_data["variant_id"],
            quantity=1, status="active",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add(extra)
        db.get(ProductVariant, batch_data["variant_id"]).stock_quantity -= 1
        db.flush()
        extra_id = extra.id
        db.commit()
    assert run_batch(test_engine, batch_size=1) == 1
    assert read_state(test_engine, batch_data) == {
        "stock": 10, "orders": {order_id: "cancelled"},
        "reservations": {reservation_id: "expired", extra_id: "expired"},
    }


def test_inactive_reservation_does_not_trigger_expiration(test_engine, batch_data, make_order):
    make_order(reservation_status="consumed")
    before = read_state(test_engine, batch_data)
    assert run_batch(test_engine) == 0
    assert read_state(test_engine, batch_data) == before
