import logging
import signal
import threading

from app.db.session import SessionLocal
from app.modules.orders.services.expiration import expire_pending_orders

logger = logging.getLogger(__name__)


def run_once(batch_size: int = 100) -> int:
    with SessionLocal() as db:
        return expire_pending_orders(db, batch_size)


def run_worker(
        interval_seconds: int = 30,
        batch_size: int = 100,
        *,
        stop_event: threading.Event | None = None
) -> None:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    if stop_event is None:
        stop_event = threading.Event()

    logger.info("Order expiration worker started")

    while not stop_event.is_set():
        try:
            proccessed = run_once(batch_size=batch_size)
            logger.info("Expired orders: %s", proccessed)
        except Exception:
            logger.exception("Order expiration batch failed")

        stop_event.wait(interval_seconds)

    logger.info("Order expiration worker stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    stop_event = threading.Event()

    def request_stop(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    run_worker(stop_event=stop_event)


if __name__ == "__main__":
    main()
