from typing import Annotated, Literal

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
)

from schemas import ProductCreate, ProductOut, ProductPage, ProductPatch
from store import Catalog


app = FastAPI(title="Product API Sprint", version="0.2.0")

app.state.catalog = Catalog()


def get_catalog(request: Request) -> Catalog:
    return request.app.state.catalog


Store = Annotated[Catalog, Depends(get_catalog)]
ProductId = Annotated[int, Path(gt=0)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ecommerce-api"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": app.version}


# Register the fixed path before the dynamic product-id path.
@app.get("/products/summary")
def summary(catalog: Store) -> dict[str, int]:
    items = catalog.all()

    return {
        "products": len(items),
        "units": sum(p.stock for p in items),
        "value_minor": sum(p.price_minor * p.stock for p in items),
    }


@app.get("/products", response_model=ProductPage)
def list_products(
    catalog: Store,
    q: str = Query(default="", max_length=80),
    min_price: int = Query(default=0, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    in_stock: bool = False,
    sort: Literal["name", "price_asc", "price_desc"] = "name",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
) -> ProductPage:

    if max_price is not None and max_price < min_price:
        raise HTTPException(422, "max_price must be >= min_price")

    items = [
        p for p in catalog.all()
        if q.casefold() in p.name.casefold()
        and p.price_minor >= min_price
        and (max_price is None or p.price_minor <= max_price)
        and (not in_stock or p.stock > 0)
    ]

    key = {
        "name": lambda p: (p.name.casefold(), p.id),
        "price_asc": lambda p: (p.price_minor, p.id),
        "price_desc": lambda p: (-p.price_minor, p.id),
    }[sort]

    items.sort(key=key)

    return ProductPage(
        items=items[offset:offset + limit],
        total=len(items),
        offset=offset,
        limit=limit,
    )



@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, catalog: Store) -> ProductOut:
    try:
        return catalog.create(data)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None

@app.get("/products/low-stock", response_model=list[ProductOut])
def low_stock(
    catalog: Store,
    threshold: int = Query(default=5, ge=0),
) -> list[ProductOut]:
    return [
        p for p in catalog.all()
        if p.stock <= threshold
    ]

@app.get("/products/{product_id}", response_model=ProductOut)
def read_product(product_id: ProductId, catalog: Store) -> ProductOut:
    try:
        return catalog.get(product_id)
    except KeyError:
        raise HTTPException(404, "Product not found") from None


@app.patch("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: ProductId,
    data: ProductPatch,
    catalog: Store,
) -> ProductOut:
    try:
        return catalog.update(product_id, data)
    except KeyError:
        raise HTTPException(404, "Product not found") from None


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: ProductId, catalog: Store) -> Response:
    try:
        catalog.delete(product_id)
    except KeyError:
        raise HTTPException(404, "Product not found") from None

    return Response(status_code=204)