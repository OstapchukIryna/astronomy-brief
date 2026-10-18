import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class Database:
    """Own an engine and the session factory for the lifetime of the app."""

    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def ping(self, timeout: float = 3.0) -> bool:
        try:
            async with asyncio.timeout(timeout):
                async with self.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
        except Exception:
            logger.warning("Database ping failed.", exc_info=True)
            return False
        return True

    async def dispose(self):
        await self.engine.dispose()


def get_database(request: Request) -> Database:
    return request.app.state.db


async def get_session(
    db: Annotated[Database, Depends(get_database)],
) -> AsyncGenerator[AsyncSession]:
    async with db.sessionmaker() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_session)]
