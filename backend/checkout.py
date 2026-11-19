
import json
import sqlite3
from contextlib import closing
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from checkout_schemas import CheckoutIn, Receipt


router = APIRouter()


def initialize_orders(path):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                request_id TEXT PRIMARY KEY NOT NULL,
                basket_json TEXT NOT NULL,
                receipt_json TEXT NOT NULL
            )
        """)
        conn.commit()


def place_order(path, data: CheckoutIn):
    # Sort so a reordered retry still represents the same basket.
    lines = sorted(data.items, key=lambda line: line.product_id)

    basket = json.dumps(
        [line.model_dump() for line in lines],
        sort_keys=True
    )

    key = str(data.request_id)

    # Explicit transaction control; do not nest catalog.transaction().
    with closing(sqlite3.connect(
        path, timeout=5, isolation_level=None
    )) as conn:
        conn.row_factory = sqlite3.Row

        try:
            conn.execute("BEGIN IMMEDIATE")

            old = conn.execute(
                "SELECT * FROM orders WHERE request_id = ?",
                (key,)
            ).fetchone()

            if old is not None:
                if old["basket_json"] != basket:
                    raise HTTPException(
                        409,
                        "Request ID used for another basket"
                    )

                conn.commit()
                return json.loads(old["receipt_json"])

            items, total = [], 0

            for line in lines:
                row = conn.execute(
                    "SELECT * FROM products WHERE id = ?",
                    (line.product_id,),
                ).fetchone()

                if row is None:
                    raise HTTPException(
                        404,
                        "Product no longer exists"
                    )

                changed = conn.execute(
                    "UPDATE products SET stock = stock - ? "
                    "WHERE id = ? AND stock >= ?",
                    (line.quantity, line.product_id, line.quantity),
                )

                if changed.rowcount != 1:
                    raise HTTPException(
                        409,
                        "Insufficient stock"
                    )

                total += row["price_minor"] * line.quantity

                items.append({
                    "product_id": line.product_id,
                    "name": row["name"],
                    "unit_price_minor": row["price_minor"],
                    "quantity": line.quantity,
                })

            receipt = {
                "request_id": key,
                "total_minor": total,
                "items": items,
            }

            conn.execute(
                "INSERT INTO orders VALUES (?, ?, ?)",
                (key, basket, json.dumps(receipt)),
            )

            conn.commit()
            return receipt

        except Exception:
            conn.rollback()
            raise


@router.post("/checkout", response_model=Receipt)
def checkout(data: CheckoutIn, request: Request):
    try:
        return place_order(request.app.state.catalog.path, data)

    except sqlite3.OperationalError as error:
        if "locked" in str(error).lower():
            raise HTTPException(
                503,
                "Database busy; retry the same request ID"
            )

        raise


@router.get("/orders/{request_id}", response_model=Receipt)
def read_order(request_id: UUID, request: Request):
    with closing(
        sqlite3.connect(request.app.state.catalog.path)
    ) as conn:
        row = conn.execute(
            "SELECT receipt_json FROM orders WHERE request_id = ?",
            (str(request_id),),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Order not found")

    return json.loads(row[0])
