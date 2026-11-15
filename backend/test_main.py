import pytest
from fastapi.testclient import TestClient

from main import app
from store import Catalog


@pytest.fixture()
def client():
    app.state.catalog = Catalog()

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
    assert client.get("/version").json() == {"version": "0.2.0"}


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
    response = client.post("/products", json=payload(**changes))
    assert response.status_code == 422


def test_required_field(client):
    data = payload()
    del data["name"]

    assert client.post("/products", json=data).status_code == 422


def test_duplicate_sku(client):
    client.post("/products", json=payload())

    response = client.post("/products", json=payload())

    assert response.status_code == 409
    assert client.get("/products").json()["total"] == 1


@pytest.mark.parametrize("changes", [
    {},
    {"stock": None},
    {"stock": -1},
    {"sku": "NEW-001"},
])
def test_invalid_patch(client, changes):
    product = client.post("/products", json=payload()).json()

    response = client.patch(
        f"/products/{product['id']}", json=changes
    )

    assert response.status_code == 422


def test_missing_product(client):
    assert client.get("/products/999").status_code == 404

    assert client.patch(
        "/products/999", json={"stock": 1}
    ).status_code == 404

    assert client.delete("/products/999").status_code == 404

def test_low_stock(client):
    client.post("/products", json=payload(stock=3))

    client.post(
        "/products",
        json=payload(sku="BOOK-002", stock=10)
    )

    response = client.get("/products/low-stock?threshold=5")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["stock"] == 3

def test_invalid_low_stock_threshold(client):
    response = client.get("/products/low-stock?threshold=-1")

    assert response.status_code == 422


@pytest.mark.parametrize("query", [
    "limit=0",
    "limit=51",
    "offset=-1",
    "sort=invalid",
    "min_price=500&max_price=100",
])
def test_invalid_query(client, query):
    assert client.get(f"/products?{query}").status_code == 422


def test_filters_sort_and_page(client):
    for row in [
        payload(),
        payload(sku="BOOK-002", name="AI Book", price_minor=4000),
        payload(sku="MOUSE-001", name="USB Mouse", stock=0),
    ]:
        assert client.post("/products", json=row).status_code == 201

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

    assert data["items"] == [] and data["total"] == 1


def test_http_and_path_errors(client):
    assert client.get("/missing").status_code == 404
    assert client.post("/health").status_code == 405
    assert client.get("/products/not-an-id").status_code == 422
    assert client.get("/products/0").status_code == 422