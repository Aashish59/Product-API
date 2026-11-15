from threading import RLock
from schemas import ProductCreate, ProductOut, ProductPatch


class Catalog:
    """Process-local store for today's API exercises."""

    def __init__(self):
        self._items: dict[int, ProductOut] = {}
        self._next_id = 1
        self._lock = RLock()

    def all(self) -> list[ProductOut]:
        with self._lock:
            return [p.model_copy() for p in self._items.values()]

    def get(self, product_id: int) -> ProductOut:
        with self._lock:
            return self._items[product_id].model_copy()

    def create(self, data: ProductCreate) -> ProductOut:
        with self._lock:
            if any(p.sku == data.sku for p in self._items.values()):
                raise ValueError("SKU already exists")

            product = ProductOut(
                id=self._next_id,
                **data.model_dump()
            )

            self._items[product.id] = product
            self._next_id += 1

            return product.model_copy()

    def update(
        self, product_id: int, changes: ProductPatch
    ) -> ProductOut:
        with self._lock:
            existing = self._items[product_id]

            merged = {
                **existing.model_dump(),
                **changes.model_dump(exclude_unset=True),
            }

            updated = ProductOut.model_validate(merged)

            self._items[product_id] = updated

            return updated.model_copy()

    def delete(self, product_id: int) -> None:
        with self._lock:
            del self._items[product_id]