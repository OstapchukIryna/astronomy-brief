import datetime as dt

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry
from app.models import Brief


class BriefRepository:
    """Store and load briefs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_date(self, date: dt.date) -> Brief | None:
        """Return the brief for a given date, or None if it isn't stored yet."""
        return await self._session.scalar(select(Brief).where(Brief.date == date))

    async def insert_if_absent(self, entry: ApodEntry) -> None:
        """Insert a brief for the entry's date unless one already exists."""
        statement = (
            insert(Brief)
            .values(
                date=entry.date,
                title=entry.title,
                explanation=entry.explanation,
                media_type=entry.media_type,
                url=entry.url,
                hd_url=entry.hd_url,
                credit=entry.credit,
            )
            .on_conflict_do_nothing(index_elements=[Brief.date])
        )
        await self._session.execute(statement)
