import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.apod import ApodEntry, ApodSource
from app.domain.dates import apod_today, ensure_valid_apod_date
from app.domain.llm import LlmClient
from app.models import Brief
from app.repositories.brief import BriefRepository, to_entry


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
        return to_entry(brief)

    async def get_explanation(self, date: dt.date) -> str:
        """Return the beginner explanation for the date, generating and saving it."""
        brief = await self._get_or_create(date)
        if brief.simple_explanation is not None:
            return brief.simple_explanation

        entry = to_entry(brief)
        await (
            self._session.rollback()
        )  # Release the connection while the LLM is working

        text = await self._llm.explain(entry)
        await self._briefs.set_explanation_if_absent(date, text)
        await self._session.commit()

        brief = await self._briefs.get_by_date(date)
        assert brief is not None and brief.simple_explanation is not None
        return brief.simple_explanation

    async def get_facts(self, date: dt.date) -> list[str]:
        """Return the requsted facts for the date, generating and saving it."""
        brief = await self._get_or_create(date)
        if brief.facts is not None:
            return brief.facts

        entry = to_entry(brief)
        await (
            self._session.rollback()
        )  # Release the connection while the LLM is working

        facts = await self._llm.extract_facts(entry)
        await self._briefs.set_facts_if_absent(date, facts)
        await self._session.commit()

        brief = await self._briefs.get_by_date(date)
        assert brief is not None and brief.facts is not None
        return brief.facts

    async def _get_or_create(self, date: dt.date) -> Brief:
        """Return the stored brief for the valid date, fetching and saving it on first request.

        The DB connection is released while the source is called, and concurrent
        requests for the same new date end up with the same stored brief.
        """
        ensure_valid_apod_date(date, today=apod_today())
        brief = await self._briefs.get_by_date(date)
        if brief is not None:
            return brief
        await (
            self._session.rollback()
        )  # Release the connection while the LLM is working

        entry = await self._source.get_entry(date)
        await self._briefs.insert_if_absent(entry)
        await self._session.commit()

        brief = await self._briefs.get_by_date(date)
        assert brief is not None, f"Brief for {date} must exist after insert"
        return brief
