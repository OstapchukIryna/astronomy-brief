import datetime as dt
from dataclasses import dataclass
from typing import Protocol

from app.domain.apod import ApodEntry
from app.domain.history import HistoryFilter, HistoryPage, PageRequest


@dataclass(frozen=True, slots=True)
class Brief:
    """Overall type that the app keeps and serves for a date NASA's entry and the generated fields together."""

    entry: ApodEntry
    simple_explanation: str | None = None
    facts: list[str] | None = None


class BriefRepository(Protocol):
    async def get_by_date(self, date: dt.date) -> Brief | None: ...

    async def insert_if_absent(self, entry: ApodEntry) -> None: ...

    async def set_explanation_if_absent(self, date: dt.date, text: str) -> None: ...

    async def set_facts_if_absent(self, date: dt.date, facts: list[str]) -> None: ...

    async def list_summaries(
        self, history_filter: HistoryFilter, page: PageRequest
    ) -> HistoryPage: ...
