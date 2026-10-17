from collections.abc import AsyncGenerator, AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import Database
from app.main import create_app


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
async def database(test_database_url: str) -> AsyncIterator[Database]:
    db = Database(test_database_url)
    yield db
    await db.dispose()
