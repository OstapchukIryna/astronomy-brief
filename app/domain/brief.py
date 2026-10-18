from dataclasses import dataclass

from app.domain.apod import ApodEntry


@dataclass(frozen=True, slots=True)
class Brief:
    """Overall type, that app keeps and serves for a date. That is the  NASA's entry and the generated fields."""

    entry: ApodEntry
    simple_explanation: str | None = None
    facts: list[str] | None = None
