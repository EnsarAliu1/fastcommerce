import pytest


@pytest.fixture
def user_a_cart(client, user_a_headers):
    response = client.post("/carts/", headers=user_a_headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_cart_without_jwt(client):
    response = client.post("/carts/")

    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"


def test_user_a_creates_cart(client, user_a_headers):
    me = client.get("/users/me", headers=user_a_headers)
    assert me.status_code == 200, me.text

    response = client.post("/carts/", headers=user_a_headers)

    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == me.json()["id"]


def test_user_a_reads_own_cart(client, user_a_headers, user_a_cart):
    response = client.get(f"/carts/{user_a_cart['id']}", headers=user_a_headers)

    assert response.status_code == 200, response.text
    assert response.json() == user_a_cart


def test_user_b_cannot_read_user_a_cart(client, user_b_headers, user_a_cart):
    response = client.get(f"/carts/{user_a_cart['id']}", headers=user_b_headers)

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Cart not found"


def test_user_b_cannot_checkout_user_a_cart(
    client, user_a_headers, user_b_headers, user_a_cart
):
    response = client.post(
        f"/carts/{user_a_cart['id']}/checkout", headers=user_b_headers
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Cart not found"
    own_cart = client.get(f"/carts/{user_a_cart['id']}", headers=user_a_headers)
    assert own_cart.status_code == 200, own_cart.text
    assert own_cart.json() == user_a_cart


def test_user_b_cannot_add_item_to_user_a_cart(
    client, user_a_headers, user_b_headers, user_a_cart
):
    response = client.post(
        f"/carts/{user_a_cart['id']}/items",
        headers=user_b_headers,
        json={"variant_id": -1, "quantity": 1},
    )

    assert response.status_code == 404, response.text
    # Ownership must fail before variant lookup, not with "Variant not found".
    assert response.json()["detail"] == "Cart not found"
    own_cart = client.get(f"/carts/{user_a_cart['id']}", headers=user_a_headers)
    assert own_cart.status_code == 200, own_cart.text
    assert own_cart.json() == user_a_cart
