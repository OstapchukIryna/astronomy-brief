import datetime as dt
from zoneinfo import ZoneInfo

FIRST_APOD_DATE = dt.date(1995, 6, 16)
_APOD_TIMEZONE = ZoneInfo("America/New_York")


class InvalidApodDateError(ValueError):
    """The date is outside the range APOD can return."""


def apod_today() -> dt.date:
    """Return today's date in the timezone NASA publishes APOD."""
    return dt.datetime.now(_APOD_TIMEZONE).date()


def ensure_valid_apod_date(date: dt.date, *, today: dt.date) -> None:
    """Raise InvalidApodDateError if APOD can't provide valid response for that date."""
    if date < FIRST_APOD_DATE:
        raise InvalidApodDateError(f"APOD starts on {FIRST_APOD_DATE}")
    if date > today:
        raise InvalidApodDateError(f"There is no APOD for {date} yet")
