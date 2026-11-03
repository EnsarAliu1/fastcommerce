import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


BACKEND = Path(__file__).resolve().parents[1]
raw_url = os.environ.get("TEST_DATABASE_URL")
if not raw_url:
    raise pytest.UsageError("Set TEST_DATABASE_URL explicitly to fastcommerce_test.")

test_url = make_url(raw_url)
if (
    test_url.drivername != "postgresql+psycopg"
    or test_url.database != "fastcommerce_test"
    or not test_url.host
    or test_url.query
):
    raise pytest.UsageError(
        "TEST_DATABASE_URL must use postgresql+psycopg, an explicit host, "
        "database fastcommerce_test and no query parameters."
    )

# Fail closed if application settings/engines were loaded before isolation.
if any(name == "app" or name.startswith("app.") for name in sys.modules):
    raise pytest.UsageError("The app was imported before test database isolation.")

os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-not-for-production-123456"
sys.path.insert(0, str(BACKEND))

# These scripts contact a running server during import; never collect them.
collect_ignore = ["manual"]


def assert_test_database(connection):
    if connection.scalar(text("SELECT current_database()")) != "fastcommerce_test":
        raise RuntimeError("Refusing to operate outside fastcommerce_test.")


@pytest.fixture(scope="session")
def test_engine():
    # The maintenance connection only creates the explicitly named test DB.
    admin_engine = create_engine(
        test_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin_engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": "fastcommerce_test"},
            )
            if not exists:
                connection.execute(text('CREATE DATABASE "fastcommerce_test"'))
    finally:
        admin_engine.dispose()

    engine = create_engine(test_url)
    try:
        with engine.connect() as connection:
            assert_test_database(connection)

        config = Config(str(BACKEND / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND / "alembic"))
        # Override the development URL in alembic.ini, escaping ConfigParser %.
        config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"].replace("%", "%%"))
        command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def client(test_engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.db import get_db
    from app.main import app

    def override_get_db():
        with Session(test_engine) as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def _test_user_data(test_engine):
    data = {"email": f"auth-{uuid4().hex}@example.com", "password": "Test-password-123!"}
    yield data
    # Real commits are allowed; remove only rows owned by this unique test user.
    with test_engine.begin() as connection:
        assert_test_database(connection)
        connection.execute(
            text(
                "DELETE FROM cart_item WHERE cart_id IN "
                "(SELECT id FROM cart WHERE user_id IN "
                "(SELECT id FROM users WHERE email = :email))"
            ),
            {"email": data["email"]},
        )
        connection.execute(
            text(
                "DELETE FROM cart WHERE user_id IN "
                "(SELECT id FROM users WHERE email = :email)"
            ),
            {"email": data["email"]},
        )
        connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": data["email"]})


@pytest.fixture
def user_data(test_engine):
    yield from _test_user_data(test_engine)


@pytest.fixture
def other_user_data(test_engine):
    yield from _test_user_data(test_engine)


def register_and_login(client, data):
    registration = client.post("/users/register", json=data)
    assert registration.status_code == 201, registration.text
    login = client.post("/users/login", json=data)
    assert login.status_code == 200, login.text
    token = login.json()
    assert token["token_type"] == "bearer"
    return {"Authorization": f"Bearer {token['access_token']}"}


@pytest.fixture
def user_a_headers(client, user_data):
    return register_and_login(client, user_data)


@pytest.fixture
def user_b_headers(client, other_user_data):
    return register_and_login(client, other_user_data)


@pytest.fixture
def checkout_data(client, test_engine, user_a_headers):
    from decimal import Decimal

    from sqlalchemy import delete, select
    from sqlalchemy.orm import Session

    from app.models import (
        Brand, Cart, CartItem, Category, Order, OrderItem,
        Product, ProductVariant, StockReservation,
    )

    me = client.get("/users/me", headers=user_a_headers)
    assert me.status_code == 200, me.text
    user_id = me.json()["id"]
    unique = uuid4().hex

    with Session(test_engine) as db:
        assert_test_database(db.connection())
        category = Category(name="Checkout category", slug=f"category-{unique}")
        brand = Brand(name="Checkout brand", slug=f"brand-{unique}")
        product = Product(
            name="Checkout product", description="Isolated checkout test",
            sku=f"product-{unique}", price=Decimal("25.00"),
            category=category, brand=brand,
        )
        variant = ProductVariant(
            product=product, sku=f"variant-{unique}",
            price=Decimal("25.00"), stock_quantity=10,
        )
        cart = Cart(user_id=user_id, status="active")
        item = CartItem(cart=cart, variant=variant, quantity=2)
        db.add(item)
        db.flush()
        data = {
            "user_id": user_id,
            "category_id": category.id,
            "brand_id": brand.id,
            "product_id": product.id,
            "variant_id": variant.id,
            "cart_id": cart.id,
            "headers": user_a_headers,
        }
        db.commit()

    try:
        yield data
    finally:
        # Find all orders for this unique user, including unexpected duplicates
        # or orders committed before a failing API response/assertion.
        with test_engine.begin() as connection:
            assert_test_database(connection)
            order_ids = select(Order.id).where(Order.user_id == user_id)
            connection.execute(delete(StockReservation).where(
                StockReservation.order_id.in_(order_ids)
            ))
            connection.execute(delete(OrderItem).where(
                OrderItem.order_id.in_(order_ids)
            ))
            connection.execute(delete(Order).where(Order.user_id == user_id))
            connection.execute(delete(CartItem).where(CartItem.cart_id == data["cart_id"]))
            connection.execute(delete(Cart).where(Cart.id == data["cart_id"]))
            connection.execute(delete(ProductVariant).where(ProductVariant.id == data["variant_id"]))
            connection.execute(delete(Product).where(Product.id == data["product_id"]))
            connection.execute(delete(Category).where(Category.id == data["category_id"]))
            connection.execute(delete(Brand).where(Brand.id == data["brand_id"]))
        # user_a_headers/user_data teardown removes the user after this fixture.
