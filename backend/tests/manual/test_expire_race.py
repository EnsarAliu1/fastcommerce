
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx

BASE_URL = "http://127.0.0.1:8000"
ORDER_ID = int(os.environ["TEST_ORDER_ID"])
ADMIN_TOKEN = os.environ["TEST_ADMIN_TOKEN"]

barrier = Barrier(2)


def expire_order():
    barrier.wait()

    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            f"{BASE_URL}/admin/orders/{ORDER_ID}/expire",
            headers={
                "Authorization": f"Bearer {ADMIN_TOKEN}"
            },
        )
        return response.status_code, response.text


with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [
        executor.submit(expire_order)
        for _ in range(2)
    ]

    for future in futures:
        print(future.result())
