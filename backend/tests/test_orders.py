from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.modules.orders.models.order import Order
from conftest import assert_test_database


@pytest.fixture
def user_a_order(client, test_engine, user_a_headers):
    response = client.get("/users/me", headers=user_a_headers)
    assert response.status_code == 200, response.text
    user_id = response.json()["id"]

    with Session(test_engine) as session:
        assert_test_database(session.connection())
        order = Order(
            status="pending", total_amount=Decimal("0.00"), user_id=user_id
        )
        session.add(order)
        session.flush()
        order_id = order.id
        session.commit()

    try:
        yield order_id
    finally:
        # This fixture depends on A's headers, so the order is removed before A.
        with test_engine.begin() as connection:
            assert_test_database(connection)
            connection.execute(delete(Order).where(Order.id == order_id))


def test_list_orders_without_jwt(client):
    response = client.get("/orders/")

    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"


def test_user_a_reads_own_order(client, user_a_headers, user_a_order):
    response = client.get(f"/orders/{user_a_order}", headers=user_a_headers)

    assert response.status_code == 200, response.text
    order = response.json()
    assert order["id"] == user_a_order
    assert order["status"] == "pending"
    assert Decimal(order["total_amount"]) == Decimal("0.00")
    assert order["items"] == []


def test_user_b_cannot_read_user_a_order(client, user_b_headers, user_a_order):
    response = client.get(f"/orders/{user_a_order}", headers=user_b_headers)

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Order not found"


def test_user_b_cannot_cancel_user_a_order(
    client, user_a_headers, user_b_headers, user_a_order
):
    response = client.post(
        f"/orders/{user_a_order}/cancel", headers=user_b_headers
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Order not found"
    own_order = client.get(f"/orders/{user_a_order}", headers=user_a_headers)
    assert own_order.status_code == 200, own_order.text
    assert own_order.json()["status"] == "pending"


def test_user_b_cannot_pay_user_a_order(
    client, user_a_headers, user_b_headers, user_a_order
):
    response = client.post(f"/orders/{user_a_order}/pay", headers=user_b_headers)

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Order not found"
    own_order = client.get(f"/orders/{user_a_order}", headers=user_a_headers)
    assert own_order.status_code == 200, own_order.text
    assert own_order.json()["status"] == "pending"


def test_user_b_orders_do_not_include_user_a_order(
    client, user_a_headers, user_b_headers, user_a_order
):
    own_orders = client.get("/orders/", headers=user_a_headers)
    assert own_orders.status_code == 200, own_orders.text
    assert user_a_order in [order["id"] for order in own_orders.json()]

    response = client.get("/orders/", headers=user_b_headers)

    assert response.status_code == 200, response.text
    assert user_a_order not in [order["id"] for order in response.json()]
    assert response.json() == []
