import datetime as dt

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry
from app.domain.brief import Brief
from app.domain.facts import Facts
from app.models import BriefRecord


def _to_brief(record: BriefRecord) -> Brief:
    """Map a stored record to the domain brief."""
    return Brief(
        entry=ApodEntry(
            date=record.date,
            title=record.title,
            explanation=record.explanation,
            media_type=record.media_type,
            url=record.url,
            hd_url=record.hd_url,
            credit=record.credit,
        ),
        simple_explanation=record.simple_explanation,
        facts=Facts(tuple(record.facts)) if record.facts is not None else None,
    )


class SqlBriefRepository:
    """Store and load briefs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_date(self, date: dt.date) -> Brief | None:
        """Return the brief for a given date or None if it wasn't stored."""
        record = await self._session.scalar(
            select(BriefRecord).where(BriefRecord.date == date)
        )
        return _to_brief(record) if record is not None else None

    async def insert_if_absent(self, entry: ApodEntry) -> None:
        """Insert a brief for the entry's date unless one already exists."""
        statement = (
            insert(BriefRecord)
            .values(
                date=entry.date,
                title=entry.title,
                explanation=entry.explanation,
                media_type=entry.media_type,
                url=entry.url,
                hd_url=entry.hd_url,
                credit=entry.credit,
            )
            .on_conflict_do_nothing(index_elements=[BriefRecord.date])
        )
        await self._session.execute(statement)

    async def set_explanation_if_absent(self, date: dt.date, text: str) -> None:
        """Save the simple explanation unless the brief already has one."""
        statement = (
            update(BriefRecord)
            .where(BriefRecord.date == date, BriefRecord.simple_explanation.is_(None))
            .values(simple_explanation=text)
        )
        await self._session.execute(statement)

    async def set_facts_if_absent(self, date: dt.date, facts: Facts) -> None:
        """Save the facts unless the brief already has them."""
        statement = (
            update(BriefRecord)
            .where(BriefRecord.date == date, BriefRecord.facts.is_(None))
            .values(facts=list(facts.items))
        )
        await self._session.execute(statement)
