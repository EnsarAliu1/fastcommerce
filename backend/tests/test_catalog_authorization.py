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
    from app.models import User

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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(params=RESOURCES)
def catalog_resource(request, test_engine):
    from app.models import Brand, Category, Product, ProductVariant

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
                    "price": "30.00", "stock_quantity": 12,
                    "size": "M", "color": "Blue",
                }
                put_payload = {**create_payload, "sku": fresh_sku(db),
                               "stock_quantity": 22}
                patch_payload = {"stock_quantity": 17}

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
