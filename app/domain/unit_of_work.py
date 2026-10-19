from types import TracebackType
from typing import Protocol, Self

from app.domain.brief import BriefRepository


class UnitOfWork(Protocol):
    """One `async with` block is one transaction. Only commit() saves the changes, exiting the block will discard them."""

    @property
    def briefs(self) -> BriefRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
