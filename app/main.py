from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import briefs, health, questions
from app.bootstrap import build_container
from app.config import Settings, get_settings
from app.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app from the settings and read them from the environment if none are given."""
    settings = settings or get_settings()
    setup_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        async with build_container(settings) as container:
            app.state.container = container
            yield

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
    app.include_router(questions.router)
    register_exception_handlers(app)

    return app
