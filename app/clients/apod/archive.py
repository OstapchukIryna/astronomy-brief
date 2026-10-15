"""APOD archive client that acts as a fallback source for APOD entries.

The old archive pages (apod.nasa.gov/apod/apYYMMDD.html) redirected to:
- article on science.nasa.gov/image-article/apod-... if the date was migrated;
- science.nasa.gov/apod/ home page.

The client resolves that redirect, downloads the article and parses it,
Handles input data with the domain errors of ApodError.
"""

import datetime as dt

import httpx

from app.clients.apod.article_parser import parse_article
from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodNotFoundError,
    ApodUnavailableError,
)

ARCHIVE_URL = "https://apod.nasa.gov/apod/"
_ARTICLE_PATH_PREFIX = "/image-article/apod-"


class ApodArchiveClient:
    """Get APOD entries from the archive pages on apod.nasa.gov and science.nasa.gov."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the APOD entry for the date.

        Raise ApodNotFoundError if the archive has no article for the date,
        ApodUnavailableError if the archive can't be reached right now,
        ApodBadResponseError if it answers with something unexpected.
        """
        article_url = await self._resolve_article_url(date)
        response = await self._get(article_url, follow_redirects=True)
        if response.status_code != httpx.codes.OK:
            raise ApodBadResponseError(
                f"Article page returned {response.status_code}: {article_url}"
            )
        return parse_article(response.text, expected_date=date)

    async def _resolve_article_url(self, date: dt.date) -> httpx.URL:
        """Return the article URL that the archive page redirects to."""
        response = await self._get(_archive_page_url(date), follow_redirects=False)

        if response.status_code == httpx.codes.NOT_FOUND:
            raise ApodNotFoundError(f"No archive page for {date}")
        if not response.is_redirect:
            raise ApodBadResponseError(
                f"Archive returned {response.status_code} for {date}"
            )

        location = response.headers.get("location")
        if not location:
            raise ApodBadResponseError(
                f"Archive redirect for {date} has no Location header"
            )

        # Location can be relative
        target = response.url.join(location)
        if not target.path.startswith(_ARTICLE_PATH_PREFIX):
            raise ApodNotFoundError(f"No article for {date}")
        return target

    async def _get(
        self, url: str | httpx.URL, *, follow_redirects: bool
    ) -> httpx.Response:
        """Send a GET request and turn transport and server failures into ApodUnavailableError."""
        try:
            response = await self._http.get(url, follow_redirects=follow_redirects)
        except httpx.TransportError as error:
            raise ApodUnavailableError(f"Archive request failed: {url}") from error
        if (
            response.is_server_error
            or response.status_code == httpx.codes.TOO_MANY_REQUESTS
        ):
            raise ApodUnavailableError(
                f"Archive returned {response.status_code}: {url}"
            )
        return response


def _archive_page_url(date: dt.date) -> str:
    """Return the old archive page URL for the date, e.g. .../apod/ap200101.html."""
    return ARCHIVE_URL + date.strftime("ap%y%m%d.html")
