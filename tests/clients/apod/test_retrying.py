import datetime as dt

import pytest

from app.clients.apod.retrying import RetryingApodSource
from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodNotFoundError,
    ApodRateLimitedError,
    ApodUnavailableError,
)
from tests.fakes import DATE, ENTRY


class FlakySource:
    """Return or raise the scripted results in order, counting calls.."""

    def __init__(self, *results: ApodEntry | Exception) -> None:
        self._results = list(results)
        self.calls = 0

    async def get_entry(self, date: dt.date) -> ApodEntry:
        result = self._results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


def retrying(inner: FlakySource) -> RetryingApodSource:
    return RetryingApodSource(inner, attempts=3, base_delay=0)


async def test_returns_entry_after_temporary_failures() -> None:
    inner = FlakySource(
        ApodUnavailableError("timeout"), ApodUnavailableError("timeout"), ENTRY
    )

    entry = await retrying(inner).get_entry(DATE)

    assert entry == ENTRY
    assert inner.calls == 3


async def test_gives_up_after_the_last_attempt() -> None:
    inner = FlakySource(*[ApodUnavailableError(f"down {n}") for n in range(3)])

    with pytest.raises(ApodUnavailableError, match="down 2"):
        await retrying(inner).get_entry(DATE)
    assert inner.calls == 3


@pytest.mark.parametrize(
    "error",
    [
        ApodNotFoundError("No article"),
        ApodBadResponseError("placeholder data"),
        ApodRateLimitedError("quota spent"),
    ],
    ids=["not-found", "bad-response", "rate-limited"],
)
async def test_does_not_retry_errors_a_retry_cannot_fix(error: Exception) -> None:
    inner = FlakySource(error, ENTRY)

    with pytest.raises(type(error)) as caught:
        await retrying(inner).get_entry(DATE)
    assert caught.value is error
    assert inner.calls == 1
