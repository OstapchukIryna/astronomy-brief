from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import briefs, health
from app.clients.apod.archive import ApodArchiveClient
from app.clients.apod.fallback import FallbackApodSource
from app.clients.apod.nasa_api import ApodApiClient
from app.clients.llm.openai_compatible import OpenAICompatibleLlmClient
from app.config import Settings, get_settings
from app.database import Database
from app.logging import setup_logging

OPENAI_BASE_URL = "https://api.openai.com/v1"


def _build_llm(
    http: httpx.AsyncClient, settings: Settings
) -> OpenAICompatibleLlmClient:
    """Create the LLM client for the configured provider."""
    if settings.llm_provider == "openai":
        assert settings.openai_api_key is not None
        return OpenAICompatibleLlmClient(
            http=http,
            base_url=OPENAI_BASE_URL,
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.llm_model,
        )
    # Else we return Ollama without key
    return OpenAICompatibleLlmClient(
        http,
        base_url=str(settings.ollama_base_url),
        api_key="ollama",
        model=settings.llm_model,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    async with (
        httpx.AsyncClient(timeout=settings.http_timeout_seconds) as http,
        httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as llm_http,
    ):
        app.state.db = Database(settings.database_url.get_secret_value())
        app.state.apod_source = FallbackApodSource(
            ApodApiClient(http, api_key=settings.nasa_api_key.get_secret_value()),
            ApodArchiveClient(http),
        )
        app.state.llm = _build_llm(llm_http, settings)
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
