import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.unit_of_work import SqlUnitOfWork
from tests.fakes import ENTRY


async def test_rolls_back_uncommited_changes_on_exit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlUnitOfWork(session_factory)
    async with uow:
        await uow.briefs.insert_if_absent(ENTRY)

    async with uow:
        assert await uow.briefs.get_by_date(ENTRY.date) is None


async def test_keeps_commited_changes_for_the_next_block(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlUnitOfWork(session_factory)
    async with uow:
        await uow.briefs.insert_if_absent(ENTRY)
        await uow.commit()

    async with uow:
        brief = await uow.briefs.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.entry == ENTRY


async def test_rolls_back_and_reraises_the_block_fails(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlUnitOfWork(session_factory)
    with pytest.raises(RuntimeError):
        async with uow:
            await uow.briefs.insert_if_absent(ENTRY)
            raise RuntimeError("boom")

    async with uow:
        assert await uow.briefs.get_by_date(ENTRY.date) is None


async def test_hides_the_repository_outside_the_block(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlUnitOfWork(session_factory)
    async with uow:
        pass

    with pytest.raises(AttributeError):
        _ = uow.briefs
