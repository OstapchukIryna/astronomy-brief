"""Shared test data and fakes for the APOD source and the LLM."""

import datetime as dt

from app.domain.apod import ApodEntry, MediaType

DATE = dt.date(2020, 1, 1)
ENTRY = ApodEntry(
    date=DATE,
    title="Betelgeuse Imagined",
    explanation="Why is Betelgeuse fading?",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)
FACTS = ["It is red.", "It is fading.", "It is far."]


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
        facts: list[str] | Exception | None = None,
    ) -> None:
        self._explanation = explanation
        self._facts = facts if facts is not None else list(FACTS)
        self.explain_calls = 0
        self.facts_calls = 0

    async def explain(self, entry: ApodEntry) -> str:
        self.explain_calls += 1
        if isinstance(self._explanation, Exception):
            raise self._explanation
        return self._explanation

    async def extract_facts(self, entry: ApodEntry) -> list[str]:
        self.facts_calls += 1
        if isinstance(self._facts, Exception):
            raise self._facts
        return self._facts
