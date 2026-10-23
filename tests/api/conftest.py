from typing import Protocol

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_container, get_session_factory
from app.bootstrap import Container
from app.database import Database
from app.domain.apod import (
    ApodSource,
)
from app.domain.llm import LlmClient
from tests.fakes import FakeLlm


class UseFakes(Protocol):
    def __call__(self, source: ApodSource, llm: LlmClient | None = None) -> None: ...


@pytest.fixture
def use_fakes(
    app: FastAPI, session_factory: async_sessionmaker[AsyncSession], database: Database
) -> UseFakes:
    """Make the app use the test unit of work and the given APOD source."""
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    def _use(source: ApodSource, llm: LlmClient | None = None) -> None:
        container = Container(db=database, apod_source=source, llm=llm or FakeLlm())
        app.dependency_overrides[get_container] = lambda: container

    return _use
