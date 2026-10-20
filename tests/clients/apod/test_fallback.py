import pytest

from app.clients.apod.fallback import FallbackApodSource
from app.domain.apod import (
    ApodBadResponseError,
    ApodError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from tests.fakes import DATE, ENTRY, FakeSource


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


async def test_reports_unavailable_when_any_source_was_unavailable() -> None:
    source = FallbackApodSource(
        FakeSource(ApodUnavailableError("API is down")),
        FakeSource(ApodNotFoundError("No article")),
    )

    with pytest.raises(ApodUnavailableError, match="API is down"):
        await source.get_entry(DATE)


@pytest.mark.parametrize(
    "errors",
    [
        pytest.param(
            (ApodBadResponseError("placeholder data"), ApodNotFoundError("No article")),
            id="bad-response-first",
        ),
        pytest.param(
            (ApodNotFoundError("No article"), ApodBadResponseError("placeholder data")),
            id="bad-response-last",
        ),
    ],
)
async def test_reports_bad_response_over_not_found(
    errors: tuple[ApodError, ApodError],
) -> None:
    source = FallbackApodSource(*(FakeSource(error) for error in errors))

    with pytest.raises(ApodBadResponseError, match="placeholder data"):
        await source.get_entry(DATE)


async def test_reports_not_found_only_when_every_source_has_no_entry() -> None:
    source = FallbackApodSource(
        FakeSource(ApodNotFoundError("No API entry")),
        FakeSource(ApodNotFoundError("No article")),
    )

    with pytest.raises(ApodNotFoundError):
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
