import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import Connection, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.database import Database
from app.main import create_app

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await transaction.rollback()


def _upgrade(connection: Connection, config: Config) -> None:
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def _migrate(url: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_upgrade, Config(ALEMBIC_INI))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database_url(test_database_url: str) -> str:
    """Bring the test database schema to head once per test session."""
    asyncio.run(_migrate(test_database_url))
    return test_database_url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = get_settings().test_database_url
    if url is None:
        pytest.exit("Set TEST_DATABASE_URL to run the tests", returncode=1)
    value = url.get_secret_value()
    if not (make_url(value).database or "").endswith("_test"):
        pytest.exit(
            "TEST_DATABASE_URL must point to a database ending with _test", returncode=1
        )
    return value


@pytest.fixture
async def database(migrated_database_url: str) -> AsyncIterator[Database]:
    db = Database(migrated_database_url)
    yield db
    await db.dispose()
