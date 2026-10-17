import datetime as dt
from collections.abc import AsyncIterator, Callable

import httpx
import pytest
import respx

from app.clients.apod.archive import ApodArchiveClient
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
)

BETELGEUSE_DATE = dt.date(2020, 1, 1)
BETELGEUSE_ARCHIVE_URL = "https://apod.nasa.gov/apod/ap200101.html"
BETELGEUSE_ARTICLE_URL = (
    "https://science.nasa.gov/image-article/apod-2020-january-1-betelgeuse-imagined"
)


@pytest.fixture
async def archive() -> AsyncIterator[ApodArchiveClient]:
    async with httpx.AsyncClient() as http:
        yield ApodArchiveClient(http)


async def test_returns_entry_for_migrated_date(
    archive: ApodArchiveClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.get(BETELGEUSE_ARCHIVE_URL).respond(
        301, headers={"Location": BETELGEUSE_ARTICLE_URL}
    )
    respx_mock.get(BETELGEUSE_ARTICLE_URL).respond(
        200, text=read_fixture("article_image.html")
    )

    entry = await archive.get_entry(BETELGEUSE_DATE)

    assert entry.title == "Betelgeuse Imagined"


async def test_raises_not_found_when_archive_redirects_to_apod_home(
    archive: ApodArchiveClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(BETELGEUSE_ARCHIVE_URL).respond(
        301, headers={"Location": "https://science.nasa.gov/apod/"}
    )

    with pytest.raises(ApodNotFoundError):
        await archive.get_entry(BETELGEUSE_DATE)


async def test_raises_not_found_when_archive_page_is_missing(
    archive: ApodArchiveClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(BETELGEUSE_ARCHIVE_URL).respond(404)

    with pytest.raises(ApodNotFoundError):
        await archive.get_entry(BETELGEUSE_DATE)


async def test_raises_bad_response_on_unexpected_archive_status(
    archive: ApodArchiveClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(BETELGEUSE_ARCHIVE_URL).respond(200, text="<html>old page</html>")

    with pytest.raises(ApodBadResponseError, match="Archive returned 200"):
        await archive.get_entry(BETELGEUSE_DATE)


async def test_raises_bad_response_when_redirect_has_no_location(
    archive: ApodArchiveClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(BETELGEUSE_ARCHIVE_URL).respond(301)

    with pytest.raises(ApodBadResponseError, match="no Location header"):
        await archive.get_entry(BETELGEUSE_DATE)


async def test_raises_bad_response_when_article_page_is_missing(
    archive: ApodArchiveClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(BETELGEUSE_ARCHIVE_URL).respond(
        301, headers={"Location": BETELGEUSE_ARTICLE_URL}
    )
    respx_mock.get(BETELGEUSE_ARTICLE_URL).respond(404)

    with pytest.raises(ApodBadResponseError, match="Article page returned 404"):
        await archive.get_entry(BETELGEUSE_DATE)
