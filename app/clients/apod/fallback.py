"""An APOD source that tries several sources in order."""

import datetime as dt
import logging

from app.domain.apod import ApodEntry, ApodError, ApodSource

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

        If a source fails, log a warning and try the next one.
        If the last source fails too, its error propagates.
        """
        *fallible, last = self._sources
        for source in fallible:
            try:
                return await source.get_entry(date)
            except ApodError as error:
                logger.warning(
                    "APOD source %s failed for %s, trying the next one: %s",
                    type(source).__name__,
                    date,
                    error,
                )
        return await last.get_entry(date)
