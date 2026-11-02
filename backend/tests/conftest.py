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


@pytest.fixture
def user_data(test_engine):
    data = {"email": f"auth-{uuid4().hex}@example.com", "password": "Test-password-123!"}
    yield data
    # Real commits are allowed in the isolated DB; remove only this test's user.
    with test_engine.begin() as connection:
        assert_test_database(connection)
        connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": data["email"]})
