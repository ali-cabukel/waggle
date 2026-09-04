"""FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from waggle.api.routers import articles, products, runs, scrapers, websocket
from waggle.jobs.scheduler import start_scheduler, stop_scheduler
from waggle.settings import settings
from waggle.storage.mongo import close_client, ensure_indexes
from waggle.storage.seed import seed_demo_scrapers


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    await seed_demo_scrapers()
    start_scheduler()
    yield
    stop_scheduler()
    await close_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Waggle API",
        description="Agentic and scheduled web scraping",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(scrapers.router, prefix="/api/v1", tags=["scrapers"])
    app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
    app.include_router(products.router, prefix="/api/v1", tags=["products"])
    app.include_router(articles.router, prefix="/api/v1", tags=["articles"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["chat"])

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
