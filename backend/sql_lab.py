
import argparse
import sqlite3

from contextlib import closing
from pathlib import Path


parser = argparse.ArgumentParser()

default = (
    Path(__file__).resolve().parent
    / "data"
    / "catalog.sqlite3"
)

parser.add_argument(
    "database",
    nargs="?",
    default=str(default),
)

args = parser.parse_args()

path = Path(args.database).resolve()

# Read-only mode stops a typo from creating an empty database.
uri = path.as_uri() + "?mode=ro"

with closing(sqlite3.connect(uri, uri=True)) as conn:

    print("Database:", path)

    print(
        "Rows:",
        conn.execute("""
            SELECT sku, name, price_minor, stock
            FROM products
            ORDER BY price_minor DESC, id
        """).fetchall(),
    )

    print(
        "Totals:",
        conn.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(stock), 0),
                COALESCE(SUM(price_minor * stock), 0)
            FROM products
        """).fetchone(),
    )

    print(
        "Plan:",
        conn.execute("""
            EXPLAIN QUERY PLAN
            SELECT id
            FROM products
            WHERE price_minor >= ?
            ORDER BY price_minor, id
            LIMIT 10
        """, (2000,)).fetchall(),
    )
