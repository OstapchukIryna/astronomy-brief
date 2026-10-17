import datetime as dt
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.history import HistoryFilter, PageRequest
from app.repositories.brief import BriefRepository
from tests.fakes import ENTRY

JAN_1 = dt.date(2020, 1, 1)
JAN_2 = dt.date(2020, 1, 2)
JAN_3 = dt.date(2020, 1, 3)
ALL = HistoryFilter()
FIRST_PAGE = PageRequest(limit=20)


async def store(
    session: AsyncSession, *entries: tuple[dt.date, str]
) -> BriefRepository:
    """Save briefs with the given dates and titles."""
    repository = BriefRepository(session)
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


async def test_more_similar_titles_come_first(session: AsyncSession) -> None:
    briefs = await store(
        session, (JAN_3, "Nebulae of Orion"), (JAN_1, "The Orion Nebula")
    )

    page = await briefs.list_summaries(HistoryFilter(keyword="nebula"), FIRST_PAGE)

    assert [item.date for item in page.items] == [JAN_1, JAN_3]


async def test_reports_next_page_only_when_there_is_one(session: AsyncSession) -> None:
    briefs = await store(session, (JAN_1, "One"), (JAN_2, "Two"), (JAN_3, "Three"))

    first = await briefs.list_summaries(ALL, PageRequest(limit=2))
    last = await briefs.list_summaries(ALL, PageRequest(limit=2, offset=2))

    assert ([item.date for item in first.items], first.has_more) == (
        [JAN_3, JAN_2],
        True,
    )
    assert ([item.date for item in last.items], last.has_more) == ([JAN_1], False)
