import logging
import threading
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

from app.workers import order_expiration as worker
from test_order_batch_expiration import (
    batch_data,
    make_order,
    read_state,
)


@pytest.fixture
def worker_db(monkeypatch, test_engine, batch_data):
    monkeypatch.setattr(
        worker,
        "SessionLocal",
        sessionmaker(bind=test_engine, autoflush=False),
    )


def test_run_once_no_expired_orders(
    worker_db, make_order, test_engine, batch_data
):
    make_order(expired=False)
    before = read_state(test_engine, batch_data)

    assert worker.run_once() == 0
    assert read_state(test_engine, batch_data) == before


def test_run_once_expired_order(
    worker_db, make_order, test_engine, batch_data
):
    order_id, reservation_id = make_order()

    assert worker.run_once() == 1
    assert read_state(test_engine, batch_data) == {
        "stock": 10,
        "orders": {order_id: "cancelled"},
        "reservations": {reservation_id: "expired"},
    }


def test_run_once_again_does_not_change_stock(
    worker_db, make_order, test_engine, batch_data
):
    make_order()

    assert worker.run_once() == 1
    before = read_state(test_engine, batch_data)

    assert worker.run_once() == 0
    assert read_state(test_engine, batch_data) == before
    assert before["stock"] == 10


def test_run_once_uses_new_session_each_time(monkeypatch):
    first = MagicMock()
    second = MagicMock()
    factory = MagicMock(side_effect=[first, second])
    service = MagicMock(return_value=0)

    monkeypatch.setattr(worker, "SessionLocal", factory)
    monkeypatch.setattr(worker, "expire_pending_orders", service)

    assert worker.run_once(7) == 0
    assert worker.run_once(7) == 0

    assert factory.call_count == 2
    assert service.call_args_list == [
        ((first.__enter__.return_value, 7), {}),
        ((second.__enter__.return_value, 7), {}),
    ]
    first.__exit__.assert_called_once()
    second.__exit__.assert_called_once()
    first.__enter__.return_value.commit.assert_not_called()
    second.__enter__.return_value.commit.assert_not_called()


def test_run_once_propagates_errors_and_closes_session(monkeypatch):
    session = MagicMock()
    session.__exit__.return_value = False
    service = MagicMock(side_effect=RuntimeError("Database unavailable"))

    monkeypatch.setattr(worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(worker, "expire_pending_orders", service)

    with pytest.raises(RuntimeError, match="Database unavailable"):
        worker.run_once()

    session.__exit__.assert_called_once()


def test_worker_logs_failure_and_continues(monkeypatch, caplog):
    # Alembic's fileConfig disables existing loggers during database setup.
    monkeypatch.setattr(worker.logger, "disabled", False)
    stop_event = threading.Event()
    calls = []
    waits = []

    def fake_run_once(batch_size):
        calls.append(batch_size)
        if len(calls) == 1:
            raise RuntimeError("Database unavailable")
        stop_event.set()
        return 1

    # Regjistron intervalin pa pritur realisht.
    def fake_wait(timeout):
        waits.append(timeout)
        return stop_event.is_set()

    monkeypatch.setattr(worker, "run_once", fake_run_once)
    monkeypatch.setattr(stop_event, "wait", fake_wait)

    with caplog.at_level(logging.INFO, logger=worker.__name__):
        worker.run_worker(batch_size=7, stop_event=stop_event)

    assert calls == [7, 7]
    assert waits == [30, 30]
    assert "Order expiration batch failed" in caplog.text
    assert "Expired orders: 1" in caplog.text
    assert any(record.exc_info for record in caplog.records)


def test_worker_stops_when_event_is_set_during_wait(monkeypatch):
    stop_event = threading.Event()
    run_once = MagicMock(return_value=0)

    def fake_wait(timeout):
        stop_event.set()
        return True

    monkeypatch.setattr(worker, "run_once", run_once)
    monkeypatch.setattr(stop_event, "wait", fake_wait)

    worker.run_worker(stop_event=stop_event)

    run_once.assert_called_once_with(batch_size=100)


def test_worker_does_not_start_batch_when_already_stopped(monkeypatch):
    stop_event = threading.Event()
    stop_event.set()
    run_once = MagicMock()
    monkeypatch.setattr(worker, "run_once", run_once)

    worker.run_worker(stop_event=stop_event)

    run_once.assert_not_called()
