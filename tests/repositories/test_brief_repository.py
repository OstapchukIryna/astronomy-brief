import datetime as dt
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry, MediaType
from app.repositories.brief import BriefRepository

ENTRY = ApodEntry(
    date=dt.date(2020, 1, 1),
    title="Betelgeuse Imagined",
    explanation="Why is Betelgeuse fading?",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)


async def test_returns_none_for_unknown_date(session: AsyncSession) -> None:
    repository = BriefRepository(session)

    assert await repository.get_by_date(ENTRY.date) is None


async def test_finds_inserted_entry_by_date(session: AsyncSession) -> None:
    repository = BriefRepository(session)

    await repository.insert_if_absent(ENTRY)
    brief = await repository.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.title == ENTRY.title
    assert brief.media_type == MediaType.IMAGE
    assert brief.simple_explanation is None


async def test_insert_if_absent_keeps_existing_brief(session: AsyncSession) -> None:
    repository = BriefRepository(session)
    await repository.insert_if_absent(ENTRY)

    await repository.insert_if_absent(replace(ENTRY, title="Another title"))
    brief = await repository.get_by_date(ENTRY.date)

    assert brief is not None
    assert brief.title == ENTRY.title
