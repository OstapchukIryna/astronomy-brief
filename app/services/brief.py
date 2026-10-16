import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodSource
from app.domain.dates import apod_today, ensure_valid_apod_date
from app.models import Brief
from app.repositories.brief import BriefRepository


class BriefService:
    """Logic around briefs."""

    def __init__(self, session: AsyncSession, source: ApodSource) -> None:
        self._session = session
        self._briefs = BriefRepository(session)
        self._source = source

    async def get_or_create(self, date: dt.date) -> Brief:
        """Return the stored brief for the valid date, fetching and saving it on first request.

        The DB connection is released while the source is called, and concurrent
        requests for the same new date end up with the same stored brief.
        """
        ensure_valid_apod_date(date, today=apod_today())
        brief = await self._briefs.get_by_date(date)
        if brief is not None:
            return brief
        await self._session.rollback()  # Releasing connection to the pool

        entry = await self._source.get_entry(date)
        await self._briefs.insert_if_absent(entry)
        await self._session.commit()

        brief = await self._briefs.get_by_date(date)
        assert brief is not None, f"Brief for {date} must exist after insert"
        return brief
