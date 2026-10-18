import datetime as dt
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry, ApodSource
from app.domain.brief import Brief
from app.domain.dates import apod_today, ensure_valid_apod_date
from app.domain.history import HistoryFilter, HistoryPage, PageRequest
from app.domain.llm import LlmClient
from app.repositories.brief import BriefRepository


class BriefService:
    """Logic around briefs."""

    def __init__(
        self, session: AsyncSession, source: ApodSource, llm: LlmClient
    ) -> None:
        self._session = session
        self._briefs = BriefRepository(session)
        self._source = source
        self._llm = llm

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the APOD entry for the valid date, fetching and saving it."""
        brief = await self._get_or_create(date)
        return brief.entry

    async def get_explanation(self, date: dt.date) -> str:
        """Return the beginner explanation for the date, generating and saving it."""
        return await self._generate_once(
            date,
            stored=lambda brief: brief.simple_explanation,
            generate=self._llm.explain,
            save=self._briefs.set_explanation_if_absent,
        )

    async def get_facts(self, date: dt.date) -> list[str]:
        """Return the facts for the date, generating and saving them."""
        return await self._generate_once(
            date,
            stored=lambda brief: brief.facts,
            generate=self._llm.extract_facts,
            save=self._briefs.set_facts_if_absent,
        )

    async def _generate_once[T](
        self,
        date: dt.date,
        *,
        stored: Callable[[Brief], T | None],
        generate: Callable[[ApodEntry], Awaitable[T]],
        save: Callable[[dt.date, T], Awaitable[None]],
    ) -> T:
        """Return a stored generated value, or generate it once and store it.

        The DB connection is released while the LLM is working. If a concurrent
        request saved its value first, that value wins and is returned.
        """
        brief = await self._get_or_create(date)
        if (value := stored(brief)) is not None:
            return value

        entry = brief.entry
        await (
            self._session.rollback()
        )  # Release the connection while the LLM is working
        await save(date, await generate(entry))
        await self._session.commit()

        brief = await self._briefs.get_by_date(date)
        assert brief is not None
        value = stored(brief)
        assert value is not None
        return value

    async def _get_or_create(self, date: dt.date) -> Brief:
        """Return the stored brief for the valid date, fetching and saving it on first request.

        The DB connection is released while the source is called, and concurrent
        requests for the same new date end up with the same stored brief.
        """
        ensure_valid_apod_date(date, today=apod_today())
        brief = await self._briefs.get_by_date(date)
        if brief is not None:
            return brief
        await self._session.rollback()

        entry = await self._source.get_entry(date)
        await self._briefs.insert_if_absent(entry)
        await self._session.commit()

        brief = await self._briefs.get_by_date(date)
        assert brief is not None, f"Brief for {date} must exist after insert"
        return brief

    async def list_history(
        self, history_filter: HistoryFilter, page: PageRequest
    ) -> HistoryPage:
        """Return one page of stored briefs that match the filter."""
        return await self._briefs.list_summaries(history_filter, page)
