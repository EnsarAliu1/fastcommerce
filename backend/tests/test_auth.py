def test_registration_success(client, user_data):
    response = client.post("/users/register", json=user_data)

    assert response.status_code == 201, response.text
    user = response.json()
    assert user["id"] > 0
    assert user["email"] == user_data["email"]
    assert user["is_active"] is True
    assert "password" not in user
    assert "hashed_password" not in user


def test_registration_duplicate_email(client, user_data):
    first = client.post("/users/register", json=user_data)
    assert first.status_code == 201, first.text

    response = client.post("/users/register", json=user_data)

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Email already registered"


def test_login_success(client, user_data):
    registration = client.post("/users/register", json=user_data)
    assert registration.status_code == 201, registration.text

    response = client.post("/users/login", json=user_data)

    assert response.status_code == 200, response.text
    token = response.json()
    assert token["token_type"] == "bearer"
    assert token["access_token"]

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["id"] == registration.json()["id"]
    assert me.json()["email"] == user_data["email"]


def test_me_without_token(client):
    response = client.get("/users/me")

    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"
