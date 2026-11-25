"""Integration tests for manual stock adjustments and their audit records."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import Brand, Category, Product, ProductVariant, StockMovement, User
from conftest import assert_test_database


OPERATIONS = ("increase-stock", "decrease-stock")


@pytest.fixture
def movement_data(client, test_engine):
    """Own all actors and catalog rows; clean up even after a partial setup."""
    marker = f"movement-{uuid4().hex}"
    user_ids = []
    actors = []
    try:
        for role in ("admin", "admin", "user"):
            credentials = {
                "email": f"{marker}-{len(actors)}@example.com",
                "password": "Test-password-123!",
            }
            response = client.post("/users/register", json=credentials)
            assert response.status_code == 201, response.text
            user_id = response.json()["id"]
            user_ids.append(user_id)
            if role == "admin":
                with test_engine.begin() as connection:
                    assert_test_database(connection)
                    connection.execute(update(User).where(User.id == user_id).values(is_admin=True))
            response = client.post("/users/login", json=credentials)
            assert response.status_code == 200, response.text
            actors.append({
                "id": user_id,
                "headers": {"Authorization": f"Bearer {response.json()['access_token']}"},
            })

        with Session(test_engine) as db:
            assert_test_database(db.connection())
            category = Category(name="Movement category", slug=marker)
            brand = Brand(name="Movement brand", slug=marker)
            db.add_all([category, brand])
            db.flush()
            product = Product(
                name="Movement product", description=marker, sku=f"product-{marker}",
                price=Decimal("25.00"), category_id=category.id, brand_id=brand.id,
            )
            db.add(product)
            db.flush()
            variants = [ProductVariant(
                product_id=product.id, sku=f"variant-{index}-{marker}",
                price=Decimal("25.00"), stock_quantity=10,
            ) for index in range(2)]
            db.add_all(variants)
            db.flush()
            variant_ids = [variant.id for variant in variants]
            db.commit()

        yield {
            "variant_id": variant_ids[0], "other_variant_id": variant_ids[1],
            "admin": actors[0], "second_admin": actors[1], "user": actors[2],
        }
    finally:
        with test_engine.begin() as connection:
            assert_test_database(connection)
            product_ids = select(Product.id).where(Product.description == marker)
            variants = select(ProductVariant.id).where(ProductVariant.product_id.in_(product_ids))
            connection.execute(delete(StockMovement).where(StockMovement.variant_id.in_(variants)))
            connection.execute(delete(ProductVariant).where(ProductVariant.product_id.in_(product_ids)))
            connection.execute(delete(Product).where(Product.description == marker))
            connection.execute(delete(Category).where(Category.slug == marker))
            connection.execute(delete(Brand).where(Brand.slug == marker))
            connection.execute(delete(User).where(User.id.in_(user_ids)))


def snapshot(test_engine, variant_id):
    """Read committed state through a fresh connection, outside request sessions."""
    with test_engine.connect() as connection:
        assert_test_database(connection)
        stock = connection.scalar(select(ProductVariant.stock_quantity).where(
            ProductVariant.id == variant_id
        ))
        movements = connection.execute(select(StockMovement.__table__).where(
            StockMovement.variant_id == variant_id
        ).order_by(StockMovement.id)).mappings().all()
        return stock, [dict(row) for row in movements]


def adjust(client, data, operation, quantity=5, reason="Physical inventory recount", actor="admin",
           variant_id=None):
    target = data["variant_id"] if variant_id is None else variant_id
    return client.post(
        f"/variants/{target}/{operation}",
        json={"quantity": quantity, "reason": reason}, headers=data[actor]["headers"],
    )


@pytest.mark.parametrize("operation, delta", (("increase-stock", 5), ("decrease-stock", -5)))
def test_adjustment_persists_correct_audit(client, test_engine, movement_data, operation, delta):
    response = adjust(client, movement_data, operation, reason="  Physical inventory recount  ")
    assert response.status_code == 200, response.text
    assert response.json()["stock_quantity"] == 10 + delta

    stock, movements = snapshot(test_engine, movement_data["variant_id"])
    assert stock == 10 + delta
    assert len(movements) == 1
    movement = movements[0]
    assert movement["variant_id"] == movement_data["variant_id"]
    assert movement["admin_id"] == movement_data["admin"]["id"]
    assert movement["movement_type"] == ("manual_increase" if delta > 0 else "manual_decrease")
    assert movement["quantity_delta"] == delta
    assert movement["stock_before"] == 10
    assert movement["stock_after"] == 10 + delta
    assert movement["reason"] == "Physical inventory recount"
    assert movement["created_at"].utcoffset() is not None


def test_insufficient_stock_leaves_no_changes(client, test_engine, movement_data):
    before = snapshot(test_engine, movement_data["variant_id"])
    response = adjust(client, movement_data, "decrease-stock", quantity=11)
    assert response.status_code == 409, response.text
    assert snapshot(test_engine, movement_data["variant_id"]) == before


def test_decrease_to_zero_is_allowed(client, test_engine, movement_data):
    response = adjust(client, movement_data, "decrease-stock", quantity=10)
    assert response.status_code == 200, response.text
    stock, movements = snapshot(test_engine, movement_data["variant_id"])
    assert stock == 0
    assert len(movements) == 1
    assert (movements[0]["stock_before"], movements[0]["stock_after"],
            movements[0]["quantity_delta"]) == (10, 0, -10)


@pytest.mark.parametrize("operation", OPERATIONS)
def test_missing_variant_has_no_movement(client, test_engine, movement_data, operation):
    # Negative IDs are absent without depending on sequence values in a shared DB.
    response = adjust(client, movement_data, operation, variant_id=-1)
    assert response.status_code == 404, response.text
    assert snapshot(test_engine, -1) == (None, [])
    assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("payload", (
    {"quantity": 5},
    {"quantity": 5, "reason": ""},
    {"quantity": 5, "reason": " \t\n "},
    {"quantity": 5, "reason": "ab"},
    {"quantity": 5, "reason": "  ab  "},
    {"quantity": 5, "reason": "x" * 501},
    {"quantity": 5, "reason": None},
    {"quantity": 5, "reason": 123},
    {"quantity": 0, "reason": "Inventory recount"},
    {"quantity": -5, "reason": "Inventory recount"},
    {"quantity": 5, "reason": "Inventory recount", "admin_id": 123},
), ids=("missing", "empty", "whitespace", "short", "short-after-trim", "long", "null",
        "wrong-type", "zero-quantity", "negative-quantity", "spoofed-admin"))
def test_invalid_adjustment_is_rejected(client, test_engine, movement_data, operation, payload):
    response = client.post(
        f"/variants/{movement_data['variant_id']}/{operation}",
        json=payload, headers=movement_data["admin"]["headers"],
    )
    assert response.status_code == 422, response.text
    assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("role, status", (("anonymous", 401), ("user", 403)))
def test_adjustments_are_admin_only(client, test_engine, movement_data, operation, role, status):
    headers = {} if role == "anonymous" else movement_data[role]["headers"]
    response = client.post(
        f"/variants/{movement_data['variant_id']}/{operation}",
        json={"quantity": 5, "reason": "Inventory recount"}, headers=headers,
    )
    assert response.status_code == status, response.text
    assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])


def test_admin_history_matches_persisted_records(client, test_engine, movement_data):
    for operation, quantity in (("increase-stock", 5), ("decrease-stock", 2)):
        response = adjust(client, movement_data, operation, quantity=quantity)
        assert response.status_code == 200, response.text
    response = adjust(client, movement_data, "increase-stock", variant_id=movement_data["other_variant_id"])
    assert response.status_code == 200, response.text

    response = client.get(
        f"/variants/{movement_data['variant_id']}/stock-movements",
        headers=movement_data["admin"]["headers"],
    )
    assert response.status_code == 200, response.text
    rows = response.json()
    stock, persisted = snapshot(test_engine, movement_data["variant_id"])
    expected = sorted(persisted, key=lambda row: (row["created_at"], row["id"]), reverse=True)
    assert stock == 13
    assert len(rows) == 2
    assert [row["id"] for row in rows] == [row["id"] for row in expected]
    for row, record in zip(rows, expected):
        assert set(row) == set(record)
        for field, value in record.items():
            if field == "created_at":
                assert datetime.fromisoformat(row[field].replace("Z", "+00:00")) == value
            else:
                assert row[field] == value


@pytest.mark.parametrize("role, status", (("anonymous", 401), ("user", 403)))
def test_history_is_admin_only(client, movement_data, role, status):
    response = client.get(
        f"/variants/{movement_data['variant_id']}/stock-movements",
        headers={} if role == "anonymous" else movement_data[role]["headers"],
    )
    assert response.status_code == status, response.text


def test_history_empty_and_missing_variant(client, movement_data):
    headers = movement_data["admin"]["headers"]
    response = client.get(f"/variants/{movement_data['variant_id']}/stock-movements", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []
    response = client.get("/variants/-1/stock-movements", headers=headers)
    assert response.status_code == 404, response.text


def test_history_pagination_and_tied_timestamps(client, test_engine, movement_data):
    for quantity in (1, 2, 3):
        response = adjust(client, movement_data, "increase-stock", quantity=quantity)
        assert response.status_code == 200, response.text
    # Explicitly exercise the secondary ID ordering, not timestamp precision.
    with test_engine.begin() as connection:
        assert_test_database(connection)
        connection.execute(update(StockMovement).where(
            StockMovement.variant_id == movement_data["variant_id"]
        ).values(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    _, records = snapshot(test_engine, movement_data["variant_id"])
    expected_ids = sorted((row["id"] for row in records), reverse=True)
    url = f"/variants/{movement_data['variant_id']}/stock-movements"
    headers = movement_data["admin"]["headers"]
    for params, expected in (({}, expected_ids), ({"limit": 2}, expected_ids[:2]),
                             ({"skip": 1, "limit": 1}, expected_ids[1:2]),
                             ({"skip": 3}, [])):
        response = client.get(url, params=params, headers=headers)
        assert response.status_code == 200, response.text
        assert [row["id"] for row in response.json()] == expected


@pytest.mark.parametrize("params", ({"skip": -1}, {"limit": 0}, {"limit": 101},
                                   {"skip": "invalid"}, {"limit": "invalid"}))
def test_history_rejects_invalid_pagination(client, movement_data, params):
    response = client.get(
        f"/variants/{movement_data['variant_id']}/stock-movements",
        params=params, headers=movement_data["admin"]["headers"],
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("operation, expected_stock", (("increase-stock", 15), ("decrease-stock", 5)))
def test_adjustment_uses_one_commit(
    client, test_engine, movement_data, monkeypatch, operation, expected_stock,
):
    original_commit = Session.commit
    commits = []

    def observe_commit(session):
        connection = session.connection()
        assert_test_database(connection)
        assert connection.scalar(select(ProductVariant.stock_quantity).where(
            ProductVariant.id == movement_data["variant_id"]
        )) == expected_stock
        session.flush()
        row = connection.execute(select(StockMovement.__table__).where(
            StockMovement.variant_id == movement_data["variant_id"]
        )).mappings().one()
        assert row["stock_before"] == 10
        assert row["stock_after"] == expected_stock
        assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])
        commits.append(row["id"])
        return original_commit(session)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", observe_commit)
        response = adjust(client, movement_data, operation)
    assert response.status_code == 200, response.text
    assert len(commits) == 1
    stock, records = snapshot(test_engine, movement_data["variant_id"])
    assert stock == expected_stock
    assert [row["id"] for row in records] == commits


@pytest.mark.parametrize("operation, expected_stock", (("increase-stock", 15), ("decrease-stock", 5)))
def test_audit_insert_database_failure_rolls_back_stock(
    client, test_engine, movement_data, operation, expected_stock,
):
    observed_updates = []

    def fail_audit_insert(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO STOCK_MOVEMENTS"):
            assert_test_database(connection)
            assert connection.scalar(select(ProductVariant.stock_quantity).where(
                ProductVariant.id == movement_data["variant_id"]
            )) == expected_stock
            observed_updates.append(expected_stock)
            # Cause a genuine PostgreSQL error in the request's transaction.
            connection.exec_driver_sql("SELECT 1 / 0")

    event.listen(test_engine, "before_cursor_execute", fail_audit_insert)
    try:
        with pytest.raises(DBAPIError):
            adjust(client, movement_data, operation)
    finally:
        event.remove(test_engine, "before_cursor_execute", fail_audit_insert)
    assert observed_updates == [expected_stock]
    assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])


@pytest.mark.parametrize("operation, expected_stock", (("increase-stock", 15), ("decrease-stock", 5)))
def test_failure_after_update_and_flushed_movement_rolls_back(
    client, test_engine, movement_data, monkeypatch, operation, expected_stock,
):
    observed_ids = []
    failure = RuntimeError("Injected failure after audit flush, before COMMIT")

    def fail_before_commit(session):
        assert session.get_bind() is test_engine
        connection = session.connection()
        assert_test_database(connection)
        # A raw connection read cannot silently autoflush pending ORM objects.
        assert connection.scalar(select(ProductVariant.stock_quantity).where(
            ProductVariant.id == movement_data["variant_id"]
        )) == expected_stock
        assert connection.execute(select(StockMovement.id).where(
            StockMovement.variant_id == movement_data["variant_id"]
        )).all() == []
        session.flush()
        movement_id = connection.execute(select(StockMovement.id).where(
            StockMovement.variant_id == movement_data["variant_id"]
        )).scalar_one()
        observed_ids.append(movement_id)
        # Another connection still sees neither uncommitted operation.
        assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_before_commit)
        with pytest.raises(RuntimeError) as caught:
            adjust(client, movement_data, operation)
    assert caught.value is failure
    assert len(observed_ids) == 1
    assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])
    # The rolled-back connection/session must not prevent a subsequent request.
    response = adjust(client, movement_data, operation)
    assert response.status_code == 200, response.text
    stock, records = snapshot(test_engine, movement_data["variant_id"])
    assert stock == expected_stock
    assert len(records) == 1
    assert records[0]["id"] not in observed_ids


def test_parallel_admin_adjustments_form_committed_sequence(client, test_engine, movement_data):
    barrier = Barrier(2)

    def synchronize_updates(connection, cursor, statement, parameters, context, executemany):
        normalized = statement.lstrip().upper()
        if normalized.startswith("UPDATE PRODUCT_VARIANTS") and "STOCK_QUANTITY" in normalized:
            barrier.wait(timeout=15)

    def increase(actor, quantity):
        return adjust(client, movement_data, "increase-stock", quantity=quantity,
                      reason=f"Concurrent recount {quantity}", actor=actor)

    # Both request sessions reach SQL UPDATE before either starts executing it.
    event.listen(test_engine, "before_cursor_execute", synchronize_updates)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(increase, "admin", 5),
                       executor.submit(increase, "second_admin", 7)]
            responses = [future.result(timeout=30) for future in futures]
    finally:
        event.remove(test_engine, "before_cursor_execute", synchronize_updates)
    assert [response.status_code for response in responses] == [200, 200], [
        response.text for response in responses
    ]
    stock, records = snapshot(test_engine, movement_data["variant_id"])
    assert stock == 22
    assert len(records) == 2
    assert sorted(row["quantity_delta"] for row in records) == [5, 7]
    ordered = sorted(records, key=lambda row: row["stock_before"])
    assert ordered[0]["stock_before"] == 10
    assert ordered[0]["stock_after"] == ordered[1]["stock_before"]
    assert ordered[1]["stock_after"] == 22
    admins = {5: movement_data["admin"]["id"], 7: movement_data["second_admin"]["id"]}
    for row in records:
        delta = row["quantity_delta"]
        assert row["stock_after"] == row["stock_before"] + delta
        assert row["movement_type"] == "manual_increase"
        assert row["admin_id"] == admins[delta]
        assert row["reason"] == f"Concurrent recount {delta}"


@pytest.mark.parametrize("changes", (
    {"stock_before": -1, "stock_after": 0, "quantity_delta": 1},
    {"stock_before": 0, "stock_after": -1, "quantity_delta": -1},
    {"stock_before": 10, "stock_after": 10, "quantity_delta": 0},
    {"stock_after": 99},
    {"movement_type": "unsupported"},
), ids=("negative-before", "negative-after", "zero-delta", "invalid-balance", "invalid-type"))
def test_database_rejects_invalid_audit_records(test_engine, movement_data, changes):
    values = {
        "variant_id": movement_data["variant_id"], "admin_id": movement_data["admin"]["id"],
        "movement_type": "manual_increase", "quantity_delta": 5,
        "stock_before": 10, "stock_after": 15, "reason": "Constraint verification",
    }
    with pytest.raises(DBAPIError):
        with test_engine.begin() as connection:
            assert_test_database(connection)
            connection.execute(StockMovement.__table__.insert().values(**{**values, **changes}))
    assert snapshot(test_engine, movement_data["variant_id"]) == (10, [])
