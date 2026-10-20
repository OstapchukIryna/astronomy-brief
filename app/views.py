"""Read-only queries that shape stored data for the API."""

from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.history import (
    KEYWORD_SIMILARITY_THRESHOLD,
    BriefSummary,
    HistoryFilter,
    HistoryPage,
    PageRequest,
)
from app.models import BriefRecord


async def list_history(
    sessions: async_sessionmaker[AsyncSession],
    history_filter: HistoryFilter,
    page: PageRequest,
) -> HistoryPage:

    statement = select(
        BriefRecord.date, BriefRecord.title, BriefRecord.media_type, BriefRecord.url
    )
    if history_filter.date_from is not None:
        statement = statement.where(BriefRecord.date >= history_filter.date_from)
    if history_filter.date_to is not None:
        statement = statement.where(BriefRecord.date <= history_filter.date_to)
    if history_filter.keyword is not None:
        keyword = literal(history_filter.keyword)
        statement = statement.where(
            keyword.op("<%", is_comparison=True)(BriefRecord.title)
        )
    if page.before is not None:
        statement = statement.where(BriefRecord.date < page.before)
    statement = statement.order_by(BriefRecord.date.desc()).limit(page.limit + 1)

    async with sessions() as session:
        if history_filter.keyword is not None:
            await session.execute(
                select(
                    func.set_config(
                        "pg_trgm.word_similarity_threshold",
                        str(KEYWORD_SIMILARITY_THRESHOLD),
                        True,
                    )
                )
            )
        rows = (await session.execute(statement)).all()
    items = tuple(
        BriefSummary(date=date, title=title, media_type=media_type, url=url)
        for date, title, media_type, url in rows[: page.limit]
    )
    next_before = items[-1].date if len(rows) > page.limit else None
    return HistoryPage(items=items, next_before=next_before)
