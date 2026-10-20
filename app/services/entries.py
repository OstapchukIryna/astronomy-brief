"""Get an APOD entry."""

import datetime as dt

from app.domain.apod import ApodSource
from app.domain.brief import Brief
from app.domain.dates import apod_today, ensure_valid_apod_date
from app.domain.unit_of_work import UnitOfWork


class EntryStore:
    """Return the stored brief for a date, fetching its entry on the first request."""

    def __init__(self, uow: UnitOfWork, source: ApodSource) -> None:
        self._uow = uow
        self._source = source

    async def get_or_create(self, date: dt.date) -> Brief:
        """Return the stored brief for the valid date, fetching and saving it.

        Concurrent requests for the same new date end up with the same stored brief.
        """
        ensure_valid_apod_date(date, today=apod_today())
        async with self._uow:
            brief = await self._uow.briefs.get_by_date(date)
        if brief is not None:
            return brief

        entry = await self._source.get_entry(date)

        async with self._uow:
            await self._uow.briefs.insert_if_absent(entry)
            brief = await self._uow.briefs.get_by_date(date)
            await self._uow.commit()

        assert brief is not None, f"Brief for {date} must exist after insert"
        return brief
