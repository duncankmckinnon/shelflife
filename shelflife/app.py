from fastapi import FastAPI

from shelflife.routers import books, import_export, reviews, shelves, tags


def create_app() -> FastAPI:
    app = FastAPI(title="Shelflife", version="0.1.0")
    app.include_router(books.router)
    app.include_router(shelves.router)
    app.include_router(reviews.router)
    app.include_router(tags.router)
    app.include_router(import_export.router)
    return app


app = create_app()
