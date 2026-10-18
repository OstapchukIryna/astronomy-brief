import datetime as dt
from dataclasses import replace

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.history import HistoryCursor, HistoryFilter, PageRequest
from app.repositories.brief import SqlBriefRepository
from tests.fakes import ENTRY

JAN_1 = dt.date(2020, 1, 1)
JAN_2 = dt.date(2020, 1, 2)
JAN_3 = dt.date(2020, 1, 3)
JAN_4 = dt.date(2020, 1, 4)
JAN_5 = dt.date(2020, 1, 5)

ALL = HistoryFilter()
FIRST_PAGE = PageRequest(limit=20)


async def store(
    session: AsyncSession, *entries: tuple[dt.date, str]
) -> SqlBriefRepository:
    """Save briefs with the given dates and titles."""
    repository = SqlBriefRepository(session)
    for date, title in entries:
        await repository.insert_if_absent(replace(ENTRY, date=date, title=title))
    return repository


async def test_returns_newest_briefs_first(session: AsyncSession) -> None:
    briefs = await store(session, (JAN_1, "Old"), (JAN_3, "New"), (JAN_2, "Middle"))

    page = await briefs.list_summaries(ALL, FIRST_PAGE)

    assert [item.date for item in page.items] == [JAN_3, JAN_2, JAN_1]


async def test_date_range_includes_both_ends(session: AsyncSession) -> None:
    briefs = await store(session, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"))

    page = await briefs.list_summaries(
        HistoryFilter(date_from=JAN_2, date_to=JAN_3), FIRST_PAGE
    )

    assert [item.date for item in page.items] == [JAN_3, JAN_2]


async def test_keyword_finds_title_despite_typo(session: AsyncSession) -> None:
    briefs = await store(
        session, (JAN_1, "Betelgeuse Imagined"), (JAN_2, "The Orion Nebula")
    )

    page = await briefs.list_summaries(HistoryFilter(keyword="betelgeus"), FIRST_PAGE)

    assert [item.title for item in page.items] == ["Betelgeuse Imagined"]


async def test_keyword_ignores_unrelated_titles(session: AsyncSession) -> None:
    briefs = await store(session, (JAN_1, "Betelgeuse Imagined"))

    page = await briefs.list_summaries(HistoryFilter(keyword="galaxy"), FIRST_PAGE)

    assert page.items == ()


async def test_search_results_come_newest_first(session: AsyncSession) -> None:
    briefs = await store(
        session, (JAN_1, "The Orion Nebula"), (JAN_3, "Nebulae of Orion")
    )

    page = await briefs.list_summaries(HistoryFilter(keyword="nebula"), FIRST_PAGE)

    assert [item.date for item in page.items] == [JAN_3, JAN_1]


async def test_gives_next_cursor_only_when_there_is_a_next_page(
    session: AsyncSession,
) -> None:
    briefs = await store(session, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"))

    first = await briefs.list_summaries(ALL, PageRequest(limit=2))
    last = await briefs.list_summaries(
        ALL, PageRequest(limit=2, after=first.next_cursor)
    )

    assert first.next_cursor == HistoryCursor(date=JAN_2)
    assert last.next_cursor is None


async def test_keyword_search_does_not_depend_on_server_threshold(
    session: AsyncSession,
) -> None:
    briefs = await store(session, (JAN_1, "Betelgeuse Imagined"))
    await session.execute(text("SET pg_trgm.word_similarity_threshold = 0.95"))

    page = await briefs.list_summaries(HistoryFilter(keyword="betelgeus"), FIRST_PAGE)

    assert [item.title for item in page.items] == ["Betelgeuse Imagined"]


async def test_next_page_skips_nothing_and_repeats_nothing_after_new_saves(
    session: AsyncSession,
) -> None:
    briefs = await store(
        session, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"), (JAN_4, "Four")
    )
    first = await briefs.list_summaries(ALL, PageRequest(limit=2))
    await store(session, (JAN_5, "Five"))

    second = await briefs.list_summaries(
        ALL, PageRequest(limit=2, after=first.next_cursor)
    )

    assert [item.date for item in second.items] == [JAN_2, JAN_1]
