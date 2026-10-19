"""Official NASA APOD API client that is the primary source for APOD entries.

Returns ApodError domain errors.
"""

import datetime as dt

import httpx
from pydantic import BaseModel, ValidationError

from app.clients.http import send
from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodRateLimitedError,
    ApodUnavailableError,
    MediaType,
)

NASA_API_URL = "https://api.nasa.gov/planetary/apod"
_PLACEHOLDER_TITLE = "NASA Science"
_PLACEHOLDER_PATH = "/wp-content/themes/"  # the NASA logo


class _ApodResponse(BaseModel):
    """The APOD API response."""

    date: dt.date
    title: str
    explanation: str
    media_type: MediaType
    url: str
    hdurl: str | None = None
    copyright: str | None = None


class ApodApiClient:
    """Get APOD entries from the official NASA API."""

    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the APOD entry for given date.

        Raise ApodUnavailableError if the API can't be reached or is overloaded,
        ApodBadResponseError if it answers with an error, a malformed body
        or placeholder data.
        """
        response = await self._get(date)
        if response.status_code != httpx.codes.OK:
            raise ApodBadResponseError(
                f"API returned {response.status_code} for {date}"
            )
        data = _parse(response, date)
        if data.title == _PLACEHOLDER_TITLE or _PLACEHOLDER_PATH in data.url:
            raise ApodBadResponseError(f"API returned placeholder data for {date}")
        if data.date != date:
            raise ApodBadResponseError(
                f"API returned the entry for {data.date} instead of {date}"
            )

        return ApodEntry(
            date=data.date,
            title=data.title,
            explanation=data.explanation,
            media_type=data.media_type,
            url=data.url,
            hd_url=data.hdurl,
            credit=data.copyright,
        )

    async def _get(self, date: dt.date) -> httpx.Response:
        """Request the entry; the API key goes in the query, so `what` has only the date."""
        return await send(
            lambda: self._http.get(
                NASA_API_URL,
                params={"date": date.isoformat(), "api_key": self._api_key},
            ),
            what=f"API request for {date}",
            unavailable=ApodUnavailableError,
            bad_response=ApodBadResponseError,
            rate_limited=ApodRateLimitedError,
        )


def _parse(response: httpx.Response, date: dt.date) -> _ApodResponse:
    """Validate the response body and raise ApodBadResponseError if it has an unexpected shape."""
    try:
        return _ApodResponse.model_validate_json(response.content)
    except ValidationError as error:
        raise ApodBadResponseError(
            f"API response for {date} has unexpected format"
        ) from error
