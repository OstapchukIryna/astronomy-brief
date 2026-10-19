from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.brief import SqlBriefRepository


class SqlUnitOfWork:
    """Open a new session for each `async with` block and roll it back unless committed.

    The repository is available only inside a block."""

    briefs: SqlBriefRepository

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
        del self.briefs

    async def commit(self) -> None:
        await self._session.commit()
