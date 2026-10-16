import datetime as dt

import pytest

from app.domain.dates import (
    FIRST_APOD_DATE,
    InvalidApodDateError,
    ensure_valid_apod_date,
)

TODAY = dt.date(2026, 10, 16)


@pytest.mark.parametrize(
    "date",
    [
        pytest.param(FIRST_APOD_DATE, id="first-apod"),
        pytest.param(dt.date(2020, 1, 1), id="ordinary"),
        pytest.param(TODAY, id="today"),
    ],
)
def test_accepts_dates_in_range(date: dt.date) -> None:
    ensure_valid_apod_date(date, today=TODAY)


@pytest.mark.parametrize(
    "date",
    [
        pytest.param(FIRST_APOD_DATE - dt.timedelta(days=1), id="before-first-apod"),
        pytest.param(TODAY + dt.timedelta(days=1), id="tomorrow"),
    ],
)
def test_rejects_dates_out_of_range(date: dt.date) -> None:
    with pytest.raises(InvalidApodDateError):
        ensure_valid_apod_date(date, today=TODAY)
