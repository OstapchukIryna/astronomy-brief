from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import health
from app.config import get_settings
from app.database import Database
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    app.state.db = Database(settings.database_url.get_secret_value())
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
    return app


app = create_app()
