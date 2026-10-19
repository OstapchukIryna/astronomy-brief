from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.brief import SqlBriefRepository


class SqlUnitOfWork:
    """Unit of work over one SQLAlchemy session.
    Open a new session for each `async with` block and roll it back unless committed."""

    brief: SqlBriefRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.briefs = SqlBriefRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()
