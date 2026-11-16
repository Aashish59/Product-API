
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from schemas import ProductCreate, ProductOut, ProductPage, ProductPatch


class ProductNotFound(Exception):
    pass


class DuplicateSKU(Exception):
    pass


class SQLiteCatalog:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    @contextmanager
    def transaction(self):
        
        conn = sqlite3.connect(
            self.path,
            timeout=5,
            autocommit=False,
        )
        conn.row_factory = sqlite3.Row
        conn.create_function(
            "CASEFOLD",
            1,
            str.casefold,
            deterministic=True,
        )

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    sku TEXT NOT NULL UNIQUE CHECK (
                        length(sku) BETWEEN 3 AND 24
                        AND sku NOT GLOB '*[^A-Z0-9-]*'
                    ),

                    name TEXT NOT NULL CHECK (
                        length(trim(name)) BETWEEN 3 AND 80
                    ),

                    price_minor INTEGER NOT NULL CHECK (
                        typeof(price_minor) = 'integer'
                        AND price_minor BETWEEN 1 AND 2000000000
                    ),

                    stock INTEGER NOT NULL CHECK (
                        typeof(stock) = 'integer'
                        AND stock BETWEEN 0 AND 1000000
                    )
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_products_price
                ON products(price_minor, id)
            """)

    @staticmethod
    def _read(conn, product_id: int) -> ProductOut:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

        if row is None:
            raise ProductNotFound()

        return ProductOut(**dict(row))

    def get(self, product_id: int) -> ProductOut:
        with self.transaction() as conn:
            return self._read(conn, product_id)

    def create(self, data: ProductCreate) -> ProductOut:
        return self.create_many([data])[0]

    def create_many(
        self,
        products: list[ProductCreate],
    ) -> list[ProductOut]:
        try:
            with self.transaction() as conn:
                created = []

                for product in products:
                    cursor = conn.execute(
                        "INSERT INTO products "
                        "(sku, name, price_minor, stock) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            product.sku,
                            product.name,
                            product.price_minor,
                            product.stock,
                        ),
                    )

                    created.append(
                        self._read(conn, cursor.lastrowid)
                    )

                return created

        except sqlite3.IntegrityError as error:
            if (
                error.sqlite_errorcode
                == sqlite3.SQLITE_CONSTRAINT_UNIQUE
            ):
                raise DuplicateSKU() from error

            # Unexpected integrity defects are not disguised as 409.
            raise

    def update(
        self,
        product_id: int,
        data: ProductPatch,
    ) -> ProductOut:
        values = data.model_dump(exclude_unset=True)

        allowed = {"name", "price_minor", "stock"}

        if not values or not values.keys() <= allowed:
            raise ValueError("Unsupported update fields")

        assignments = ", ".join(
            f"{key} = ?" for key in values
        )

        with self.transaction() as conn:
            cursor = conn.execute(
                f"UPDATE products SET {assignments} WHERE id = ?",
                [*values.values(), product_id],
            )

            if cursor.rowcount == 0:
                raise ProductNotFound()

            return self._read(conn, product_id)

    def delete(self, product_id: int):
        with self.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,),
            )

            if cursor.rowcount == 0:
                raise ProductNotFound()

    def page(
        self,
        q,
        min_price,
        max_price,
        in_stock,
        sort,
        offset,
        limit,
    ) -> ProductPage:
        conditions = [
            "instr(CASEFOLD(name), CASEFOLD(?)) > 0",
            "price_minor >= ?",
        ]

        params = [q, min_price]

        if max_price is not None:
            conditions.append("price_minor <= ?")
            params.append(max_price)

        if in_stock:
            conditions.append("stock > 0")

        where = " AND ".join(conditions)

        # SQL identifiers cannot be bound as values.
        # Use a fixed allowlist instead.
        order = {
            "name": "CASEFOLD(name), id",
            "price_asc": "price_minor, id",
            "price_desc": "price_minor DESC, id",
        }[sort]

        with self.transaction() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM products WHERE {where}",
                params,
            ).fetchone()[0]

            rows = conn.execute(
                f"SELECT * FROM products WHERE {where} "
                f"ORDER BY {order} LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()

            return ProductPage(
                items=[
                    ProductOut(**dict(row))
                    for row in rows
                ],
                total=total,
                offset=offset,
                limit=limit,
            )

    def low_stock(
        self,
        threshold: int,
    ) -> list[ProductOut]:
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM products "
                "WHERE stock <= ? ORDER BY stock, id",
                (threshold,),
            ).fetchall()

            return [
                ProductOut(**dict(row))
                for row in rows
            ]

    def summary(self) -> dict[str, int]:
        with self.transaction() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS products,
                    COALESCE(SUM(stock), 0) AS units,
                    COALESCE(SUM(price_minor * stock), 0)
                        AS value_minor
                FROM products
            """).fetchone()

            return dict(row)
