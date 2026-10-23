"""Shared test data and fakes for the APOD source and the LLM."""

import datetime as dt
from dataclasses import replace
from types import TracebackType
from typing import Self

from app.domain.apod import ApodEntry, MediaType
from app.domain.brief import Brief
from app.domain.facts import Facts
from app.domain.questions import Question

DATE = dt.date(2020, 1, 1)
ENTRY = ApodEntry(
    date=DATE,
    title="Betelgeuse Imagined",
    explanation="Why is Betelgeuse fading?",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)
FACTS = Facts(("It is red.", "It is fading.", "It is far."))


class FakeSource:
    """Returns a fixed entry or raises a fixed error, and counts calls."""

    def __init__(self, result: ApodEntry | Exception = ENTRY) -> None:
        self._result = result
        self.calls = 0

    async def get_entry(self, date: dt.date) -> ApodEntry:
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class FakeLlm:
    """Returns fixed answers or raises fixed errors, and counts calls."""

    def __init__(
        self,
        explanation: str | Exception = "A star is fading.",
        facts: Facts | Exception = FACTS,
        on_topic: bool | Exception = True,
        answer: str | Exception = "It is losing brightness.",
    ) -> None:
        self._explanation = explanation
        self._facts = facts
        self._on_topic = on_topic
        self._answer = answer
        self.explain_calls = 0
        self.facts_calls = 0
        self.classified: list[tuple[ApodEntry, Question]] = []
        self.answered: list[tuple[ApodEntry, Question]] = []

    async def explain(self, entry: ApodEntry) -> str:
        self.explain_calls += 1
        if isinstance(self._explanation, Exception):
            raise self._explanation
        return self._explanation

    async def extract_facts(self, entry: ApodEntry) -> Facts:
        self.facts_calls += 1
        if isinstance(self._facts, Exception):
            raise self._facts
        return self._facts

    async def is_on_topic(self, entry: ApodEntry, question: Question) -> bool:
        self.classified.append((entry, question))
        if isinstance(self._on_topic, Exception):
            raise self._on_topic
        return self._on_topic

    async def answer(self, entry: ApodEntry, question: Question) -> str:
        self.answered.append((entry, question))
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


class FakeBriefRepository:
    """Keeps briefs in memory."""

    def __init__(self) -> None:
        self._briefs: dict[dt.date, Brief] = {}

    async def get_by_date(self, date: dt.date) -> Brief | None:
        return self._briefs.get(date)

    async def insert_if_absent(self, entry: ApodEntry) -> None:
        self._briefs.setdefault(entry.date, Brief(entry=entry))

    async def set_explanation_if_absent(self, date: dt.date, text: str) -> None:
        brief = self._briefs.get(date)
        if brief is not None and brief.simple_explanation is None:
            self._briefs[date] = replace(brief, simple_explanation=text)

    async def set_facts_if_absent(self, date: dt.date, facts: Facts) -> None:
        brief = self._briefs.get(date)
        if brief is not None and brief.facts is None:
            self._briefs[date] = replace(brief, facts=facts)


class FakeUnitOfWork:
    """In-memory unit of work without real rolling back.
    It saves changes, counts commits, tracks open blocks."""

    def __init__(self) -> None:
        self.briefs = FakeBriefRepository()
        self.commits = 0
        self.in_transaction = False

    async def __aenter__(self) -> Self:
        assert not self.in_transaction, "Unit of work blocks must not be nested"
        self.in_transaction = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.in_transaction = False

    async def commit(self) -> None:
        assert self.in_transaction, "commit() must be called inside a block"
        self.commits += 1
