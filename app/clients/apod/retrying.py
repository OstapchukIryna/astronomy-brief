"""An APOD source that retries another source while it is unavailable."""

import datetime as dt
import logging

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.domain.apod import (
    ApodEntry,
    ApodRateLimitedError,
    ApodSource,
    ApodUnavailableError,
)

logger = logging.getLogger(__name__)


class RetryingApodSource:
    def __init__(
        self, inner: ApodSource, *, attempts: int = 3, base_delay: float = 0.5
    ) -> None:
        self._inner = inner
        self._attempts = attempts
        self._base_delay = base_delay

    async def get_entry(self, date: dt.date) -> ApodEntry:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(ApodUnavailableError)
            & retry_if_not_exception_type(ApodRateLimitedError),
            stop=stop_after_attempt(self._attempts),
            wait=wait_exponential_jitter(
                multiplier=self._base_delay, jitter=self._base_delay
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        ):
            with attempt:
                return await self._inner.get_entry(date)
        raise AssertionError("unreachable")
