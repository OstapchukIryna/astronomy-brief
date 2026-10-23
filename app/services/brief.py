import datetime as dt
from collections.abc import Awaitable, Callable

from app.domain.apod import ApodEntry
from app.domain.brief import Brief, BriefRepository
from app.domain.facts import Facts
from app.domain.llm import BriefLlm
from app.domain.unit_of_work import UnitOfWork
from app.services.entries import EntryStore


class BriefService:
    """Get APOD entries, generate their explanations and facts once, and list the stored history."""

    def __init__(self, uow: UnitOfWork, entries: EntryStore, llm: BriefLlm) -> None:
        self._uow = uow
        self._entries = entries
        self._llm = llm

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the APOD entry for the valid date, fetching and saving it."""
        brief = await self._entries.get_or_create(date)
        return brief.entry

    async def get_explanation(self, date: dt.date) -> str:
        """Return the beginner explanation for the date, generating and saving it."""
        return await self._generate_once(
            date,
            stored=lambda brief: brief.simple_explanation,
            generate=self._llm.explain,
            save=lambda briefs, text: briefs.set_explanation_if_absent(date, text),
        )

    async def get_facts(self, date: dt.date) -> Facts:
        """Return the facts for the date, generating and saving them."""
        return await self._generate_once(
            date,
            stored=lambda brief: brief.facts,
            generate=self._llm.extract_facts,
            save=lambda briefs, facts: briefs.set_facts_if_absent(date, facts),
        )

    async def _generate_once[T](
        self,
        date: dt.date,
        *,
        stored: Callable[[Brief], T | None],
        generate: Callable[[ApodEntry], Awaitable[T]],
        save: Callable[[BriefRepository, T], Awaitable[None]],
    ) -> T:
        """Return a stored generated value, or generate it once and store it.

        If a concurrent request saved its value first, that value wins and is returned.
        """
        brief = await self._entries.get_or_create(date)
        if (value := stored(brief)) is not None:
            return value

        generated = await generate(brief.entry)
        async with self._uow:
            await save(self._uow.briefs, generated)
            brief = await self._uow.briefs.get_by_date(date)
            await self._uow.commit()

        assert brief is not None, f"Brief for {date} must exist after saving"
        value = stored(brief)
        assert value is not None, f"Generated value for {date} must be stored"
        return value
