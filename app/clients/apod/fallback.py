"""An APOD source that tries several sources in order."""

import datetime as dt
import logging

from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodError,
    ApodSource,
    ApodUnavailableError,
)

logger = logging.getLogger(__name__)


class FallbackApodSource:
    """Try APOD sources in order and return the first occured entry."""

    def __init__(self, *sources: ApodSource) -> None:
        if not sources:
            raise ValueError("At least one APOD source is required")
        self._sources = sources

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the entry from the first source that has it.

        If every source fails, raise the most important error:
        - ApodUnavailableError if any source was unavailable, since a retry may help;
        - ApodBadResponseError if any source returned data we couldn't use;
        - ApodNotFoundError only when every source had no entry for the date.
        """
        errors: list[ApodError] = []

        for source in self._sources:
            try:
                return await source.get_entry(date)
            except ApodError as error:
                logger.warning("APOD source %r failed for %s: %s", source, date, error)
                errors.append(error)

        for kind in (ApodUnavailableError, ApodBadResponseError):
            if found := next(
                (error for error in errors if isinstance(error, kind)), None
            ):
                raise found
        raise errors[-1]
