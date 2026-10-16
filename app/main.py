from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import briefs, health
from app.clients.apod.archive import ApodArchiveClient
from app.clients.apod.fallback import FallbackApodSource
from app.clients.apod.nasa_api import ApodApiClient
from app.config import get_settings
from app.database import Database
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as http:
        app.state.db = Database(settings.database_url.get_secret_value())
        app.state.apod_source = FallbackApodSource(
            ApodApiClient(http, api_key=settings.nasa_api_key.get_secret_value()),
            ApodArchiveClient(http),
        )
        try:
            yield
        finally:
            await app.state.db.dispose()


def create_app() -> FastAPI:
    setup_logging(get_settings())
    app = FastAPI(
        title="AI Astronomy Daily Brief",
        description=(
            "Educational API that explains NASA's Astronomy Picture of the Day "
            "for non-experts using an LLM."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(briefs.router)
    register_exception_handlers(app)

    return app


app = create_app()
