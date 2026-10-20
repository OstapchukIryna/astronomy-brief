"""Build the app's long-lived dependencies in one place (the composition root)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from app.clients.apod.article import ApodArticleClient
from app.clients.apod.fallback import FallbackApodSource
from app.clients.apod.nasa_api import ApodApiClient
from app.clients.apod.retrying import RetryingApodSource
from app.clients.llm.openai_compatible import OpenAICompatibleLlmClient
from app.config import Settings
from app.database import Database
from app.domain.apod import ApodSource
from app.domain.llm import LlmClient

OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True, slots=True)
class Container:
    """The dependencies for the app."""

    db: Database
    apod_source: ApodSource
    llm: LlmClient


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container]:
    """Create the dependencies for the settings and close them on exit."""
    async with (
        httpx.AsyncClient(timeout=settings.http_timeout_seconds) as http,
        httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as llm_http,
    ):
        db = Database(settings.database_url.get_secret_value())
        try:
            yield Container(
                db=db,
                apod_source=FallbackApodSource(
                    RetryingApodSource(
                        ApodApiClient(
                            http, api_key=settings.nasa_api_key.get_secret_value()
                        )
                    ),
                    RetryingApodSource(ApodArticleClient(http)),
                ),
                llm=_build_llm(llm_http, settings),
            )

        finally:
            await db.dispose()


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
