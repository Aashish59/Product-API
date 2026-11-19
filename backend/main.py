
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from catalog import SQLiteCatalog
from routes import router


def create_app(db_path: str | Path | None = None) -> FastAPI:
    default = (
        Path(__file__).resolve().parent
        / "data"
        / "catalog.sqlite3"
    )

    chosen = (
        db_path
        if db_path is not None
        else os.getenv("CATALOG_DB", default)
    )

    path = Path(chosen).resolve()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        catalog = SQLiteCatalog(path)
        catalog.initialize()
        app.state.catalog = catalog

        yield

    app = FastAPI(
        title="Persistent Product API",
        version="0.3.0",
        lifespan=lifespan,
    )

    app.include_router(router)
    app.include_router(checkout_router)

    return app


app = create_app()
