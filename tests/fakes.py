import datetime as dt

from app.domain.apod import ApodEntry


class FakeSource:
    """Returns a fixed entry or raises a fixed error, and counts calls."""

    def __init__(self, result: ApodEntry | Exception) -> None:
        self._result = result
        self.calls = 0

    async def get_entry(self, date: dt.date) -> ApodEntry:
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result
