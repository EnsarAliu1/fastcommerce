import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx


BASE_URL = "http://127.0.0.1:8000"
ORDER_ID = 14

USER_TOKEN = os.environ["TEST_USER_TOKEN"]
ADMIN_TOKEN = os.environ["TEST_ADMIN_TOKEN"]

barrier = Barrier(2)


def send_request(name, path, token):
    with httpx.Client(timeout=30.0) as client:
        barrier.wait(timeout=10)

        response = client.post(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
        )

        return name, response.status_code, response.text


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as executor:
        pay = executor.submit(
            send_request,
            "pay",
            f"/orders/{ORDER_ID}/pay",
            USER_TOKEN,
        )
        expire = executor.submit(
            send_request,
            "expire",
            f"/admin/orders/{ORDER_ID}/expire",
            ADMIN_TOKEN,
        )

        results = [pay.result(), expire.result()]

    for name, status, body in results:
        print(f"{name}: {status}\n{body}\n")

    statuses = {name: status for name, status, _ in results}
    assert statuses == {"pay": 409, "expire": 200}, statuses
