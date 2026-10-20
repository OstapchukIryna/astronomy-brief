import datetime as dt
from dataclasses import replace

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import views
from app.domain.history import HistoryFilter, PageRequest
from app.repositories.unit_of_work import SqlUnitOfWork
from tests.fakes import ENTRY

JAN_1 = dt.date(2020, 1, 1)
JAN_2 = dt.date(2020, 1, 2)
JAN_3 = dt.date(2020, 1, 3)
JAN_4 = dt.date(2020, 1, 4)
JAN_5 = dt.date(2020, 1, 5)

ALL = HistoryFilter()
FIRST_PAGE = PageRequest(limit=20)

Sessions = async_sessionmaker[AsyncSession]


async def store(uow: SqlUnitOfWork, *entries: tuple[dt.date, str]) -> None:
    """Save and commit briefs with the given dates and titles."""
    async with uow:
        for date, title in entries:
            await uow.briefs.insert_if_absent(replace(ENTRY, date=date, title=title))
        await uow.commit()


async def test_returns_newest_briefs_first(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "Old"), (JAN_3, "New"), (JAN_2, "Middle"))

    page = await views.list_history(session_factory, ALL, FIRST_PAGE)

    assert [item.date for item in page.items] == [JAN_3, JAN_2, JAN_1]


async def test_date_range_includes_both_ends(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"))

    page = await views.list_history(
        session_factory, HistoryFilter(date_from=JAN_2, date_to=JAN_3), FIRST_PAGE
    )

    assert [item.date for item in page.items] == [JAN_3, JAN_2]


async def test_keyword_finds_title_despite_typo(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "Betelgeuse Imagined"), (JAN_2, "The Orion Nebula"))

    page = await views.list_history(
        session_factory, HistoryFilter(keyword="betelgeus"), FIRST_PAGE
    )

    assert [item.title for item in page.items] == ["Betelgeuse Imagined"]


async def test_keyword_ignores_unrelated_titles(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "Betelgeuse Imagined"))

    page = await views.list_history(
        session_factory, HistoryFilter(keyword="galaxy"), FIRST_PAGE
    )

    assert page.items == ()


async def test_search_results_come_newest_first(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "The Orion Nebula"), (JAN_3, "Nebulae of Orion"))

    page = await views.list_history(
        session_factory, HistoryFilter(keyword="nebula"), FIRST_PAGE
    )

    assert [item.date for item in page.items] == [JAN_3, JAN_1]


async def test_gives_next_before_only_when_there_is_a_next_page(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"))

    first = await views.list_history(session_factory, ALL, PageRequest(limit=2))
    last = await views.list_history(
        session_factory, ALL, PageRequest(limit=2, before=first.next_before)
    )

    assert first.next_before == JAN_2
    assert last.next_before is None


async def test_keyword_search_does_not_depend_on_server_threshold(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "Betelgeuse Imagined"))
    async with session_factory() as session:
        await session.execute(text("SET pg_trgm.word_similarity_threshold = 0.95"))
        await session.commit()

    page = await views.list_history(
        session_factory, HistoryFilter(keyword="betelgeus"), FIRST_PAGE
    )

    assert [item.title for item in page.items] == ["Betelgeuse Imagined"]


async def test_next_page_skips_nothing_and_repeats_nothing_after_new_saves(
    uow: SqlUnitOfWork, session_factory: Sessions
) -> None:
    await store(uow, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"), (JAN_4, "Four"))
    first = await views.list_history(session_factory, ALL, PageRequest(limit=2))
    await store(uow, (JAN_5, "Five"))

    second = await views.list_history(
        session_factory, ALL, PageRequest(limit=2, before=first.next_before)
    )

    assert [item.date for item in second.items] == [JAN_2, JAN_1]
