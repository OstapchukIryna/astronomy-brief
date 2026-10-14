import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ApodEntry:
    date: dt.date
    title: str
    explanation: str
    media_type: MediaType
    url: str
    hd_url: str | None = None
    credit: str | None = None


class ApodError(Exception):
    """Base class for all APOD source errors."""


class ApodNotFoundError(ApodError):
    """No record exists for the requested data."""


class ApodUnavailableError(ApodError):
    """The source is temporarily unavailable."""


class ApodBadResponseError(ApodError):
    """The source responded, but received data is not what was expected."""


class ApodSource(Protocol):
    async def get_entry(self, date: dt.date) -> ApodEntry: ...
