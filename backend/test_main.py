
import sqlite3

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(tmp_path / "test.sqlite3")

    with TestClient(app) as test_client:
        yield test_client


def payload(**changes):
    data = {
        "sku": "BOOK-001",
        "name": "Python Book",
        "price_minor": 2500,
        "stock": 3,
    }

    return {**data, **changes}


def test_system_routes(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/version").json() == {"version": "0.3.0"}


def test_create_read_patch_delete(client):
    response = client.post("/products", json=payload())
    assert response.status_code == 201

    product = response.json()
    url = f"/products/{product['id']}"

    assert client.get(url).json() == product

    response = client.patch(url, json={"stock": 0})
    assert response.status_code == 200
    assert response.json()["stock"] == 0
    assert response.json()["name"] == product["name"]

    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""

    assert client.get(url).status_code == 404


@pytest.mark.parametrize("changes", [
    {"name": " "},
    {"price_minor": -1},
    {"stock": -1},
    {"sku": "bad sku"},
    {"price_minor": 2.5},
    {"stock": True},
    {"unknown_field": 1},
])
def test_invalid_create(client, changes):
    response = client.post(
        "/products",
        json=payload(**changes),
    )

    assert response.status_code == 422


def test_required_field(client):
    data = payload()
    del data["name"]

    assert client.post(
        "/products",
        json=data,
    ).status_code == 422


def test_duplicate_sku(client):
    client.post("/products", json=payload())

    response = client.post(
        "/products",
        json=payload(),
    )

    assert response.status_code == 409
    assert client.get("/products").json()["total"] == 1


@pytest.mark.parametrize("changes", [
    {},
    {"stock": None},
    {"stock": -1},
    {"sku": "NEW-001"},
])
def test_invalid_patch(client, changes):
    product = client.post(
        "/products",
        json=payload(),
    ).json()

    response = client.patch(
        f"/products/{product['id']}",
        json=changes,
    )

    assert response.status_code == 422


def test_missing_product(client):
    assert client.get("/products/999").status_code == 404

    assert client.patch(
        "/products/999",
        json={"stock": 1},
    ).status_code == 404

    assert client.delete("/products/999").status_code == 404


@pytest.mark.parametrize("query", [
    "limit=0",
    "limit=51",
    "offset=-1",
    "sort=invalid",
    "min_price=500&max_price=100",
])
def test_invalid_query(client, query):
    assert client.get(
        f"/products?{query}"
    ).status_code == 422


def test_filters_sort_and_page(client):
    for row in [
        payload(),
        payload(
            sku="BOOK-002",
            name="AI Book",
            price_minor=4000,
        ),
        payload(
            sku="MOUSE-001",
            name="USB Mouse",
            stock=0,
        ),
    ]:
        assert client.post(
            "/products",
            json=row,
        ).status_code == 201

    response = client.get(
        "/products?q=book&in_stock=true&min_price=2000"
        "&max_price=5000&sort=price_desc&offset=1&limit=1"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["sku"] == "BOOK-001"


def test_summary_and_empty_page(client):
    assert client.get("/products").json()["items"] == []

    client.post("/products", json=payload())

    assert client.get("/products/summary").json() == {
        "products": 1,
        "units": 3,
        "value_minor": 7500,
    }

    data = client.get("/products?offset=100").json()

    assert data["items"] == []
    assert data["total"] == 1


def test_http_and_path_errors(client):
    assert client.get("/missing").status_code == 404
    assert client.post("/health").status_code == 405
    assert client.get("/products/not-an-id").status_code == 422
    assert client.get("/products/0").status_code == 422


def test_persists_across_app_instances(tmp_path):
    path = tmp_path / "persist.sqlite3"

    with TestClient(create_app(path)) as first:
        created = first.post(
            "/products",
            json=payload(),
        ).json()

    # A new app and connections use the same database file.
    with TestClient(create_app(path)) as second:
        response = second.get(
            f"/products/{created['id']}"
        )

        assert response.status_code == 200
        assert response.json() == created


def test_batch_success(client):
    rows = [
        payload(),
        payload(
            sku="BOOK-002",
            name="AI Book",
        ),
    ]

    response = client.post(
        "/products/batch",
        json={"products": rows},
    )

    assert response.status_code == 201
    assert len(response.json()) == 2
    assert client.get("/products").json()["total"] == 2


def test_batch_rolls_back_existing_duplicate(client):
    client.post("/products", json=payload())

    rows = [
        payload(sku="NEW-001"),
        payload(),
    ]

    response = client.post(
        "/products/batch",
        json={"products": rows},
    )

    assert response.status_code == 409

    page = client.get("/products").json()

    assert page["total"] == 1
    assert [p["sku"] for p in page["items"]] == [
        "BOOK-001"
    ]


def test_batch_rolls_back_internal_duplicate(client):
    response = client.post(
        "/products/batch",
        json={"products": [payload(), payload()]},
    )

    assert response.status_code == 409
    assert client.get("/products").json()["total"] == 0


@pytest.mark.parametrize("size", [0, 21])
def test_batch_size_limit(client, size):
    rows = [
        payload(sku=f"BOOK-{i:03}")
        for i in range(size)
    ]

    response = client.post(
        "/products/batch",
        json={"products": rows},
    )

    assert response.status_code == 422


def test_valid_write_after_rollback(client):
    client.post(
        "/products/batch",
        json={"products": [payload(), payload()]},
    )

    response = client.post(
        "/products",
        json=payload(sku="RECOVER-001"),
    )

    assert response.status_code == 201
    assert client.get("/products").json()["total"] == 1


def test_quotes_in_search_are_data(client):
    client.post(
        "/products",
        json=payload(name="SQL' Book"),
    )

    assert client.get(
        "/products",
        params={"q": "SQL'"},
    ).json()["total"] == 1

    response = client.get(
        "/products",
        params={"q": "' OR 1=1 --"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert client.get("/products").json()["total"] == 1


@pytest.mark.parametrize("price,stock", [
    (-1, 1),
    (100, -1),
])
def test_database_rejects_invalid_direct_write(
    tmp_path,
    price,
    stock,
):
    path = tmp_path / "constraints.sqlite3"

    with TestClient(create_app(path)):
        pass  # Run startup to initialize the database.

    conn = sqlite3.connect(path, autocommit=False)

    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO products "
                "(sku,name,price_minor,stock) "
                "VALUES (?,?,?,?)",
                ("RAW-001", "Raw Item", price, stock),
            )

        conn.rollback()

    finally:
        conn.close()


def test_empty_summary_has_integer_zeroes(client):
    assert client.get("/products/summary").json() == {
        "products": 0,
        "units": 0,
        "value_minor": 0,
    }


def test_unicode_casefold_search(client):
    client.post(
        "/products",
        json=payload(name="Straße Book"),
    )

    data = client.get(
        "/products",
        params={"q": "STRASSE"},
    ).json()

    assert data["total"] == 1


@pytest.mark.parametrize("changes", [
    {"price_minor": 2000000001},
    {"stock": 1000001},
])
def test_new_numeric_bounds(client, changes):
    response = client.post(
        "/products",
        json=payload(**changes),
    )

    assert response.status_code == 422


def test_apps_with_different_database_files_are_isolated(
    tmp_path,
):
    with TestClient(
        create_app(tmp_path / "a.sqlite3")
    ) as first:
        first.post("/products", json=payload())

    with TestClient(
        create_app(tmp_path / "b.sqlite3")
    ) as second:
        assert second.get("/products").json()["total"] == 0


@pytest.mark.parametrize("url", [
    "/products/9223372036854775808",
    "/products?min_price=2000000001",
    "/products?max_price=2000000001",
])
def test_sql_integer_limits_are_validated(client, url):
    assert client.get(url).status_code == 422


def test_low_stock_feature_is_preserved(client):
    client.post("/products", json=payload())

    client.post(
        "/products",
        json=payload(sku="ZERO-001", stock=0),
    )

    data = client.get(
        "/products/low-stock?threshold=0"
    ).json()

    assert [p["sku"] for p in data] == ["ZERO-001"]

    assert len(
        client.get(
            "/products/low-stock?threshold=3"
        ).json()
    ) == 2

    assert client.get(
        "/products/low-stock?threshold=-1"
    ).status_code == 422
