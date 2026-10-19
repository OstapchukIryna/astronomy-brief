"""An APOD source that tries several sources in order."""

import datetime as dt
import logging

from app.domain.apod import ApodEntry, ApodError, ApodSource, ApodUnavailableError

logger = logging.getLogger(__name__)


class FallbackApodSource:
    """Try APOD sources in order and return the first entry that one of them gives.

    Implements ApodSource itself, so the caller doesn't know there are several sources.
    """

    def __init__(self, *sources: ApodSource) -> None:
        if not sources:
            raise ValueError("At least one APOD source is required")
        self._sources = sources

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the entry from the first source that has it.

        If every source fails, raise ApodUnavailableError if any source was unavailable,
        since a retry may find the entry, otherwise raise the last source's error.
        """
        errors: list[ApodError] = []

        for source in self._sources:
            try:
                return await source.get_entry(date)
            except ApodError as error:
                logger.warning(
                    "APOD source %s failed for %s: %s",
                    type(source).__name__,
                    date,
                    error,
                )
                errors.append(error)

        unavailable = next(
            (error for error in errors if isinstance(error, ApodUnavailableError)), None
        )
        raise unavailable or errors[-1]
