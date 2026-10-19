from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import briefs, health
from app.bootstrap import build_container
from app.config import get_settings
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    async with build_container(get_settings()) as container:
        app.state.container = container
        yield


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
