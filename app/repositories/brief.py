import datetime as dt

from sqlalchemy import func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry
from app.domain.history import (
    KEYWORD_SIMILARITY_THRESHOLD,
    BriefSummary,
    HistoryCursor,
    HistoryFilter,
    HistoryPage,
    PageRequest,
)
from app.models import Brief


def to_entry(brief: Brief) -> ApodEntry:
    """Convert a stored brief back to the APOD entry."""
    return ApodEntry(
        date=brief.date,
        title=brief.title,
        explanation=brief.explanation,
        media_type=brief.media_type,
        url=brief.url,
        hd_url=brief.hd_url,
        credit=brief.credit,
    )


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

    async def set_explanation_if_absent(self, date: dt.date, text: str) -> None:
        """Save the simple explanation unless the brief already has one."""
        statement = (
            update(Brief)
            .where(Brief.date == date, Brief.simple_explanation.is_(None))
            .values(simple_explanation=text)
        )
        await self._session.execute(statement)

    async def set_facts_if_absent(self, date: dt.date, facts: list[str]) -> None:
        """Save the facts unless the brief already has them."""
        statement = (
            update(Brief)
            .where(Brief.date == date, Brief.facts.is_(None))
            .values(facts=facts)
        )
        await self._session.execute(statement)

    async def list_summaries(
        self, history_filter: HistoryFilter, page: PageRequest
    ) -> HistoryPage:
        """Return one page of stored briefs that match the filter, newest first."""
        if history_filter.keyword is not None:
            await self._session.execute(
                select(
                    func.set_config(
                        "pg_trgm.word_similarity_threshold",
                        str(KEYWORD_SIMILARITY_THRESHOLD),
                        True,
                    )
                )
            )

        statement = select(Brief.date, Brief.title, Brief.media_type, Brief.url)
        if history_filter.date_from is not None:
            statement = statement.where(Brief.date >= history_filter.date_from)
        if history_filter.date_to is not None:
            statement = statement.where(Brief.date <= history_filter.date_to)
        if history_filter.keyword is not None:
            keyword = literal(history_filter.keyword)
            statement = statement.where(
                keyword.op("<%", is_comparison=True)(Brief.title)
            )
        if page.after is not None:
            statement = statement.where(Brief.date < page.after.date)
        statement = (
            statement.order_by(Brief.date.desc())
            .limit(page.limit + 1)  # one extra row tells whether there is a next page
            .offset(page.offset)
        )

        rows = (await self._session.execute(statement)).all()
        items = tuple(
            BriefSummary(date=date, title=title, media_type=media_type, url=url)
            for date, title, media_type, url in rows[: page.limit]
        )
        has_more = len(rows) > page.limit
        next_cursor = HistoryCursor(date=items[-1].date) if has_more else None
        return HistoryPage(items=items, has_more=has_more, next_cursor=next_cursor)
