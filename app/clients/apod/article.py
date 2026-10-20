"""APOD source that finds the article for a date on science.nasa.gov.

NASA moved APOD to science.nasa.gov, where every picture is an "image-article"
published on its APOD date, with a slug like apod-2020-january-1-<title>.
The client asks the site's WordPress REST API for the APOD article published
that day, then downloads and parses its page.
"""

import datetime as dt

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.clients.apod.article_parser import parse_article
from app.clients.http import send
from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodNotFoundError,
    ApodRateLimitedError,
    ApodUnavailableError,
)

ARTICLES_URL = "https://science.nasa.gov/wp-json/wp/v2/image-article"


class _Article(BaseModel):
    """An article in the WordPress REST API response."""

    slug: str
    link: str


_ARTICLES = TypeAdapter(list[_Article])


class ApodArticleClient:
    """Get APOD entries from their articles on science.nasa.gov."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def get_entry(self, date: dt.date) -> ApodEntry:
        """Return the APOD entry for the date.

        Raise ApodNotFoundError if no APOD article was published that day,
        ApodUnavailableError if science.nasa.gov can't be reached right now,
        ApodBadResponseError if it answers with something unexpected.
        """
        article_url = await self._find_article_url(date)
        response = await self._get(article_url)
        if response.status_code != httpx.codes.OK:
            raise ApodBadResponseError(
                f"Article page returned {response.status_code}: {article_url}"
            )
        return parse_article(response.text, expected_date=date)

    async def _find_article_url(self, date: dt.date) -> str:
        """Return the link of the first APOD article published on the date."""
        response = await self._get(ARTICLES_URL, params=_published_on(date))
        if response.status_code != httpx.codes.OK:
            raise ApodBadResponseError(
                f"Article search returned {response.status_code} for {date}"
            )
        try:
            articles = _ARTICLES.validate_json(response.content)
        except ValidationError as error:
            raise ApodBadResponseError(
                f"Article search returned unexpected data for {date}"
            ) from error

        prefix = _slug_prefix(date)
        for article in articles:
            if article.slug.startswith(prefix):
                return article.link
        raise ApodNotFoundError(f"No APOD article published on {date}")

    async def _get(
        self, url: str, *, params: dict[str, str] | None = None
    ) -> httpx.Response:
        return await send(
            lambda: self._http.get(url, params=params, follow_redirects=True),
            what=f"Article request {url}",
            unavailable=ApodUnavailableError,
            bad_response=ApodBadResponseError,
            rate_limited=ApodRateLimitedError,
        )


def _published_on(date: dt.date) -> dict[str, str]:
    """Return the query for APOD articles published on the date in ASC order.

    `after` and `before` are exclusive.
    """
    return {
        "after": f"{date - dt.timedelta(days=1)}T23:59:59",
        "before": f"{date + dt.timedelta(days=1)}T00:00:00",
        "orderby": "date",
        "order": "asc",
        "_fields": "slug,link",
    }


def _slug_prefix(date: dt.date) -> str:
    """Return start of the slug, e.g. apod-2020-january-1-.

    The trailing dash split January 1 and January 10.
    """
    month = date.strftime("%B").lower()
    return f"apod-{date.year}-{month}-{date.day}-"
