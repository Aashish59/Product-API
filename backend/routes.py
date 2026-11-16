
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
)

from catalog import SQLiteCatalog, DuplicateSKU, ProductNotFound

from schemas import (
    ProductBatch,
    ProductCreate,
    ProductOut,
    ProductPage,
    ProductPatch,
)


router = APIRouter()


def get_catalog(request: Request) -> SQLiteCatalog:
    return request.app.state.catalog


Store = Annotated[SQLiteCatalog, Depends(get_catalog)]

ProductId = Annotated[
    int,
    Path(gt=0, le=9_223_372_036_854_775_807),
]


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ecommerce-api",
    }


@router.get("/version")
def version(request: Request) -> dict[str, str]:
    return {"version": request.app.version}


@router.get("/products/summary")
def summary(catalog: Store) -> dict[str, int]:
    return catalog.summary()


@router.get("/products", response_model=ProductPage)
def list_products(
    catalog: Store,
    q: str = Query(default="", max_length=80),
    min_price: int = Query(
        default=0,
        ge=0,
        le=2_000_000_000,
    ),
    max_price: int | None = Query(
        default=None,
        ge=0,
        le=2_000_000_000,
    ),
    in_stock: bool = False,
    sort: Literal[
        "name",
        "price_asc",
        "price_desc",
    ] = "name",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
) -> ProductPage:

    if max_price is not None and max_price < min_price:
        raise HTTPException(
            422,
            "max_price must be >= min_price",
        )

    return catalog.page(
        q,
        min_price,
        max_price,
        in_stock,
        sort,
        offset,
        limit,
    )


@router.post(
    "/products",
    response_model=ProductOut,
    status_code=201,
)
def create_product(
    data: ProductCreate,
    catalog: Store,
) -> ProductOut:
    try:
        return catalog.create(data)

    except DuplicateSKU:
        raise HTTPException(
            409,
            "SKU already exists",
        ) from None


@router.post(
    "/products/batch",
    response_model=list[ProductOut],
    status_code=201,
)
def create_batch(
    data: ProductBatch,
    catalog: Store,
) -> list[ProductOut]:
    try:
        return catalog.create_many(data.products)

    except DuplicateSKU:
        raise HTTPException(
            409,
            "Batch contains a duplicate SKU",
        ) from None


@router.get(
    "/products/low-stock",
    response_model=list[ProductOut],
)
def low_stock(
    catalog: Store,
    threshold: int = Query(
        default=2,
        ge=0,
        le=1_000_000,
    ),
) -> list[ProductOut]:

    return catalog.low_stock(threshold)


@router.get(
    "/products/{product_id}",
    response_model=ProductOut,
)
def read_product(
    product_id: ProductId,
    catalog: Store,
) -> ProductOut:
    try:
        return catalog.get(product_id)

    except ProductNotFound:
        raise HTTPException(
            404,
            "Product not found",
        ) from None


@router.patch(
    "/products/{product_id}",
    response_model=ProductOut,
)
def update_product(
    product_id: ProductId,
    data: ProductPatch,
    catalog: Store,
) -> ProductOut:
    try:
        return catalog.update(product_id, data)

    except ProductNotFound:
        raise HTTPException(
            404,
            "Product not found",
        ) from None


@router.delete(
    "/products/{product_id}",
    status_code=204,
)
def delete_product(
    product_id: ProductId,
    catalog: Store,
) -> Response:
    try:
        catalog.delete(product_id)

    except ProductNotFound:
        raise HTTPException(
            404,
            "Product not found",
        ) from None

    return Response(status_code=204)
