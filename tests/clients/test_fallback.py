import datetime as dt

import pytest

from app.clients.apod.fallback import FallbackApodSource
from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodNotFoundError,
    ApodUnavailableError,
    MediaType,
)
from tests.fakes import FakeSource

DATE = dt.date(2020, 1, 1)
ENTRY = ApodEntry(
    date=DATE,
    title="Betelgeuse Imagined",
    explanation="Why is Betelgeuse fading?",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)


async def test_returns_entry_from_first_source_without_asking_the_next() -> None:
    first = FakeSource(ENTRY)
    second = FakeSource(ENTRY)
    source = FallbackApodSource(first, second)

    entry = await source.get_entry(DATE)

    assert entry == ENTRY
    assert second.calls == 0


async def test_falls_back_when_first_source_fails() -> None:
    source = FallbackApodSource(
        FakeSource(ApodBadResponseError("placeholder data")),
        FakeSource(ENTRY),
    )

    entry = await source.get_entry(DATE)

    assert entry == ENTRY


async def test_raises_last_error_when_all_sources_fail() -> None:
    source = FallbackApodSource(
        FakeSource(ApodUnavailableError("API is down")),
        FakeSource(ApodNotFoundError("No article")),
    )

    with pytest.raises(ApodNotFoundError, match="No article"):
        await source.get_entry(DATE)


async def test_does_not_hide_unexpected_errors() -> None:
    second = FakeSource(ENTRY)
    source = FallbackApodSource(FakeSource(KeyError("bug")), second)

    with pytest.raises(KeyError):
        await source.get_entry(DATE)
    assert second.calls == 0


async def test_logs_warning_on_fallback(caplog: pytest.LogCaptureFixture) -> None:
    source = FallbackApodSource(
        FakeSource(ApodBadResponseError("placeholder data")),
        FakeSource(ENTRY),
    )

    await source.get_entry(DATE)

    assert "FakeSource" in caplog.text
    assert "2020-01-01" in caplog.text
    assert "placeholder data" in caplog.text


def test_requires_at_least_one_source() -> None:
    with pytest.raises(ValueError, match="At least one"):
        FallbackApodSource()
