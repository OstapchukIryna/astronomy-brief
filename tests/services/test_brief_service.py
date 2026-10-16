import datetime as dt
from dataclasses import replace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry, ApodNotFoundError, MediaType
from app.repositories.brief import BriefRepository
from app.services.brief import BriefService
from tests.fakes import FakeSource

DATE = dt.date(2020, 1, 1)
ENTRY = ApodEntry(
    date=DATE,
    title="Betelgeuse Imagined",
    explanation="Why is Betelgeuse fading?",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)


async def test_returns_stored_brief_without_calling_source(
    session: AsyncSession,
) -> None:
    await BriefRepository(session).insert_if_absent(ENTRY)
    source = FakeSource(ENTRY)

    brief = await BriefService(session, source).get_or_create(DATE)

    assert brief.title == ENTRY.title
    assert source.calls == 0


async def test_fetches_and_stores_missing_brief(session: AsyncSession) -> None:
    source = FakeSource(ENTRY)

    brief = await BriefService(session, source).get_or_create(DATE)

    assert brief.title == ENTRY.title
    assert source.calls == 1
    assert await BriefRepository(session).get_by_date(DATE) is not None


async def test_stores_nothing_when_source_fails(session: AsyncSession) -> None:
    service = BriefService(session, FakeSource(ApodNotFoundError("No article")))

    with pytest.raises(ApodNotFoundError):
        await service.get_or_create(DATE)

    assert await BriefRepository(session).get_by_date(DATE) is None


class RacingSource:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = BriefRepository(session)

    async def get_entry(self, date: dt.date) -> ApodEntry:
        await self._repository.insert_if_absent(
            replace(ENTRY, title="Saved by another request")
        )
        return ENTRY


async def test_returns_brief_saved_by_concurrent_request(session: AsyncSession) -> None:
    brief = await BriefService(session, RacingSource(session)).get_or_create(DATE)

    assert brief.title == "Saved by another request"
