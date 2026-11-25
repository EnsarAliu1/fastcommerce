"""Catalog authorization through real JWTs and the isolated test database."""

from decimal import Decimal
import secrets
import string
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from conftest import assert_test_database


RESOURCES = ("products", "categories", "brands", "variants")
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


@pytest.fixture
def admin_headers(client, test_engine, other_user_data):
    # Register through the public API; promotion happens only in the test DB.
    from app.models import StockMovement, User

    response = client.post("/users/register", json=other_user_data)
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    with test_engine.begin() as connection:
        assert_test_database(connection)
        result = connection.execute(
            update(User).where(User.id == user_id).values(is_admin=True)
        )
        assert result.rowcount == 1

    response = client.post("/users/login", json=other_user_data)
    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    try:
        yield {"Authorization": f"Bearer {response.json()['access_token']}"}
    finally:
        # Remove audit references before other_user_data deletes this admin.
        with test_engine.begin() as connection:
            assert_test_database(connection)
            connection.execute(delete(StockMovement).where(StockMovement.admin_id == user_id))


@pytest.fixture(params=RESOURCES)
def catalog_resource(request, test_engine):
    from app.models import Brand, Category, Product, ProductVariant, StockMovement

    resource = request.param
    marker = f"catalog-auth-{uuid4().hex}"
    slugs = [f"{marker}-{suffix}" for suffix in ("base", "target", "new", "put")]
    skus = []

    def fresh_sku(db):
        # API schemas require ABC-123, so UUIDs cannot be used as SKU payloads.
        while True:
            sku = "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))
            sku += f"-{secrets.randbelow(1000):03d}"
            if sku in skus:
                continue
            if any(db.scalar(select(model.id).where(model.sku == sku)) is not None
                   for model in (Product, ProductVariant)):
                continue
            skus.append(sku)
            return sku

    try:
        with Session(test_engine) as db:
            assert_test_database(db.connection())
            category = Category(name="Authorization category", slug=slugs[0])
            brand = Brand(name="Authorization brand", slug=slugs[0])
            db.add_all([category, brand])
            db.flush()
            product = Product(
                name="Authorization product", description=marker,
                price=Decimal("25.00"), sku=fresh_sku(db),
                category_id=category.id, brand_id=brand.id,
            )
            db.add(product)
            db.flush()
            product_payload = {
                "name": "Created product", "description": marker,
                "price": "30.00", "sku": fresh_sku(db),
                "category_id": category.id, "brand_id": brand.id,
            }
            if resource in ("categories", "brands"):
                model = Category if resource == "categories" else Brand
                # An empty target allows DELETE to succeed under business rules.
                target = model(name="Authorization target", slug=slugs[1])
                db.add(target)
                create_payload = {"name": "Created entry", "slug": slugs[2]}
                put_payload = {"name": "Replaced entry", "slug": slugs[3]}
                patch_payload = {"name": "Patched entry"}
            elif resource == "products":
                target = product
                create_payload = product_payload
                put_payload = {**product_payload, "name": "Replaced product",
                               "sku": fresh_sku(db)}
                patch_payload = {"name": "Patched product", "price": "35.00"}
            else:
                target = ProductVariant(
                    product_id=product.id, sku=fresh_sku(db),
                    price=Decimal("25.00"), stock_quantity=10,
                )
                db.add(target)
                create_payload = {
                    "product_id": product.id, "sku": fresh_sku(db),
                    "price": "30.00", "stock_quantity": 10,
                    "size": "M", "color": "Blue",
                }
                put_payload = {
                    key: value for key, value in create_payload.items()
                    if key != "stock_quantity"
                }
                put_payload["sku"] = fresh_sku(db)
                patch_payload = {"price": "35.00", "color": "Red"}

            db.flush()
            data = {
                "resource": resource,
                "collection": f"/{resource}/" if resource in ("products", "variants")
                              else f"/{resource}",
                "detail": f"/{resource}/{target.id}",
                "id": target.id,
                "POST": create_payload, "PUT": put_payload, "PATCH": patch_payload,
                "populated_detail": f"/{resource}/{category.id if resource == 'categories' else brand.id}",
            }
            db.commit()

        yield data
    finally:
        # Select by fixture-owned markers, including rows committed by API calls
        # before an assertion fails. Never truncate shared tables.
        with test_engine.begin() as connection:
            assert_test_database(connection)
            product_ids = select(Product.id).where(Product.description == marker)
            variant_ids = select(ProductVariant.id).where(
                ProductVariant.product_id.in_(product_ids)
            )
            connection.execute(delete(StockMovement).where(
                StockMovement.variant_id.in_(variant_ids)
            ))
            connection.execute(delete(ProductVariant).where(
                ProductVariant.product_id.in_(product_ids)
            ))
            connection.execute(delete(Product).where(Product.description == marker))
            connection.execute(delete(Category).where(Category.slug.in_(slugs)))
            connection.execute(delete(Brand).where(Brand.slug.in_(slugs)))


def write_request(client, data, method, headers):
    url = data["collection"] if method == "POST" else data["detail"]
    kwargs = {"headers": headers}
    if method != "DELETE":
        kwargs["json"] = data[method]
    return client.request(method, url, **kwargs)


@pytest.mark.parametrize("endpoint", ("collection", "detail"))
def test_catalog_get_is_public(client, catalog_resource, endpoint):
    response = client.get(catalog_resource[endpoint])
    assert response.status_code == 200, response.text
    if endpoint == "collection":
        assert any(row["id"] == catalog_resource["id"] for row in response.json())
    else:
        assert response.json()["id"] == catalog_resource["id"]


@pytest.mark.parametrize("method", WRITE_METHODS)
@pytest.mark.parametrize("role, expected_status", (("anonymous", 401), ("user", 403)))
def test_catalog_writes_require_admin(
    client, catalog_resource, method, role, expected_status, request,
):
    headers = {} if role == "anonymous" else request.getfixturevalue("user_a_headers")
    before = client.get(catalog_resource["collection"])
    assert before.status_code == 200, before.text

    response = write_request(client, catalog_resource, method, headers)

    assert response.status_code == expected_status, response.text
    if role == "anonymous":
        assert response.headers["www-authenticate"] == "Bearer"
    else:
        assert response.json()["detail"] == "Admin access required"
    after = client.get(catalog_resource["collection"])
    assert after.status_code == 200, after.text
    # Rejected creates, updates, deletes and stock changes must have no effect.
    assert sorted(after.json(), key=lambda row: row["id"]) == sorted(
        before.json(), key=lambda row: row["id"]
    )


@pytest.mark.parametrize("method", WRITE_METHODS)
def test_admin_can_write_catalog(client, catalog_resource, admin_headers, method):
    check_stock = catalog_resource["resource"] == "variants" and method in ("PUT", "PATCH")
    if check_stock:
        before = client.get(catalog_resource["detail"])
        assert before.status_code == 200, before.text

    response = write_request(client, catalog_resource, method, admin_headers)

    assert response.status_code == (201 if method == "POST" else
                                    204 if method == "DELETE" else 200), response.text
    if method == "DELETE":
        assert response.content == b""
        assert client.get(catalog_resource["detail"]).status_code == 404
        return

    body = response.json()
    if method != "POST":
        assert body["id"] == catalog_resource["id"]
    persisted = client.get(f"/{catalog_resource['resource']}/{body['id']}")
    assert persisted.status_code == 200, persisted.text
    if check_stock:
        assert body["stock_quantity"] == before.json()["stock_quantity"]
        assert persisted.json()["stock_quantity"] == before.json()["stock_quantity"]
    for field, expected in catalog_resource[method].items():
        actual = persisted.json()[field]
        if field == "price":
            assert Decimal(str(actual)) == Decimal(expected)
        else:
            assert actual == expected


@pytest.mark.parametrize("catalog_resource", ("categories", "brands"), indirect=True)
def test_admin_cannot_delete_populated_category_or_brand(
    client, catalog_resource, admin_headers,
):
    url = catalog_resource["populated_detail"]
    response = client.delete(url, headers=admin_headers)
    assert response.status_code == 409, response.text
    assert client.get(url).status_code == 200


@pytest.mark.parametrize("catalog_resource", ("variants",), indirect=True)
@pytest.mark.parametrize("method", ("PUT", "PATCH"))
@pytest.mark.parametrize("stock_quantity", (500, 0, None, 10))
def test_admin_cannot_set_stock_through_catalog(
    client, catalog_resource, admin_headers, method, stock_quantity,
):
    before = client.get(catalog_resource["detail"])
    assert before.status_code == 200, before.text
    # Include valid catalog changes too: rejection must leave the entire row
    # unchanged, and a PUT must not fail merely because required fields are absent.
    payload = {**catalog_resource[method], "stock_quantity": stock_quantity}

    response = client.request(
        method, catalog_resource["detail"], json=payload, headers=admin_headers,
    )

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", "stock_quantity"]
        and error["type"] == "extra_forbidden"
        for error in response.json()["detail"]
    ), response.text
    after = client.get(catalog_resource["detail"])
    assert after.status_code == 200, after.text
    assert after.json() == before.json()


@pytest.mark.parametrize("catalog_resource", ("variants",), indirect=True)
@pytest.mark.parametrize("missing_field", ("product_id", "sku", "price"))
def test_variant_put_still_requires_complete_catalog_fields(
    client, catalog_resource, admin_headers, missing_field,
):
    before = client.get(catalog_resource["detail"])
    assert before.status_code == 200, before.text
    payload = dict(catalog_resource["PUT"])
    del payload[missing_field]

    response = client.put(
        catalog_resource["detail"], json=payload, headers=admin_headers,
    )

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", missing_field] and error["type"] == "missing"
        for error in response.json()["detail"]
    ), response.text
    after = client.get(catalog_resource["detail"])
    assert after.status_code == 200, after.text
    assert after.json() == before.json()


@pytest.mark.parametrize("catalog_resource", ("variants",), indirect=True)
def test_admin_can_create_variant_without_initial_stock(
    client, catalog_resource, admin_headers,
):
    payload = dict(catalog_resource["POST"])
    del payload["stock_quantity"]

    response = client.post(
        catalog_resource["collection"], json=payload, headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["stock_quantity"] == 0
    persisted = client.get(f"/variants/{response.json()['id']}")
    assert persisted.status_code == 200, persisted.text
    assert persisted.json()["stock_quantity"] == 0


@pytest.mark.parametrize("catalog_resource", ("variants",), indirect=True)
@pytest.mark.parametrize("operation, delta", (("increase-stock", 4), ("decrease-stock", -4)))
def test_admin_can_adjust_stock_through_inventory(
    client, catalog_resource, admin_headers, operation, delta,
):
    before = client.get(catalog_resource["detail"])
    assert before.status_code == 200, before.text
    expected_stock = before.json()["stock_quantity"] + delta

    response = client.post(
        f"{catalog_resource['detail']}/{operation}",
        json={"quantity": abs(delta), "reason": "Catalog authorization test"},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["stock_quantity"] == expected_stock
    after = client.get(catalog_resource["detail"])
    assert after.status_code == 200, after.text
    assert after.json()["stock_quantity"] == expected_stock
    assert after.json() == {**before.json(), "stock_quantity": expected_stock}


@pytest.mark.parametrize("catalog_resource", ("variants",), indirect=True)
@pytest.mark.parametrize("operation", ("increase-stock", "decrease-stock"))
@pytest.mark.parametrize("role, expected_status", (("anonymous", 401), ("user", 403)))
def test_inventory_stock_adjustments_require_admin(
    client, catalog_resource, operation, role, expected_status, request,
):
    headers = {} if role == "anonymous" else request.getfixturevalue("user_a_headers")
    before = client.get(catalog_resource["detail"])
    assert before.status_code == 200, before.text

    response = client.post(
        f"{catalog_resource['detail']}/{operation}",
        json={"quantity": 4, "reason": "Catalog authorization test"}, headers=headers,
    )

    assert response.status_code == expected_status, response.text
    if role == "anonymous":
        assert response.headers["www-authenticate"] == "Bearer"
    else:
        assert response.json()["detail"] == "Admin access required"
    after = client.get(catalog_resource["detail"])
    assert after.status_code == 200, after.text
    assert after.json() == before.json()
