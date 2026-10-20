import datetime as dt
import unicodedata
from dataclasses import dataclass

from app.domain.apod import MediaType

MIN_KEYWORD_LENGTH = 3  # shorter keywords match too many titles by chance
MAX_KEYWORD_LENGTH = 100
MAX_PAGE_SIZE = 100
KEYWORD_SIMILARITY_THRESHOLD = 0.6  # how close a title word must be to count as found


class InvalidHistoryFilterError(ValueError):
    """The history request breaks one of its rules."""


@dataclass(frozen=True)
class HistoryFilter:
    """Conditions for searching stored briefs. Every condition is optional."""

    date_from: dt.date | None = None
    date_to: dt.date | None = None
    keyword: str | None = None

    def __post_init__(self) -> None:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise InvalidHistoryFilterError(
                f"Start date {self.date_from} is after end date {self.date_to}"
            )
        if self.keyword is not None:
            keyword = self.keyword.strip()
            if not MIN_KEYWORD_LENGTH <= len(keyword) <= MAX_KEYWORD_LENGTH:
                raise InvalidHistoryFilterError(
                    f"The keyword must be {MIN_KEYWORD_LENGTH} to "
                    f"{MAX_KEYWORD_LENGTH} characters long"
                )
            if any(unicodedata.category(char) == "Cc" for char in keyword):
                raise InvalidHistoryFilterError(
                    "The keyword must not contain control characters"
                )  # "Cc" stands for («Other, control») in Unicode
            object.__setattr__(self, "keyword", keyword)


@dataclass(frozen=True, slots=True)
class PageRequest:
    """Which part of the result have to be returned. Up to `limit` briefs dated before `before`."""

    limit: int
    before: dt.date | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_PAGE_SIZE:
            raise InvalidHistoryFilterError(
                f"The page size must be 1 to {MAX_PAGE_SIZE}"
            )


@dataclass(frozen=True, slots=True)
class BriefSummary:
    """A short card of a stored brief."""

    date: dt.date
    title: str
    media_type: MediaType
    url: str


@dataclass(frozen=True, slots=True)
class HistoryPage:
    """One page of history and the date as a cursor."""

    items: tuple[BriefSummary, ...]
    next_before: dt.date | None
