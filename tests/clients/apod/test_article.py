import datetime as dt
from collections.abc import Callable

import httpx
import pytest
import respx

from app.clients.apod.article import ARTICLES_URL, ApodArticleClient
from app.domain.apod import ApodBadResponseError, ApodNotFoundError

BETELGEUSE_DATE = dt.date(2020, 1, 1)
BETELGEUSE_ARTICLE_URL = (
    "https://science.nasa.gov/image-article/apod-2020-january-1-betelgeuse-imagined/"
)


@pytest.fixture
def articles(http: httpx.AsyncClient) -> ApodArticleClient:
    return ApodArticleClient(http)


async def test_returns_entry_for_date(
    articles: ApodArticleClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.get(ARTICLES_URL).respond(
        200, text=read_fixture("wp_image_articles.json")
    )
    respx_mock.get(BETELGEUSE_ARTICLE_URL).respond(
        200, text=read_fixture("article_image.html")
    )

    entry = await articles.get_entry(BETELGEUSE_DATE)

    assert entry.title == "Betelgeuse Imagined"


async def test_asks_for_articles_published_on_the_date(
    articles: ApodArticleClient, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(ARTICLES_URL).respond(200, json=[])

    with pytest.raises(ApodNotFoundError):
        await articles.get_entry(BETELGEUSE_DATE)

    params = route.calls.last.request.url.params
    assert params["after"] == "2019-12-31T23:59:59"
    assert params["before"] == "2020-01-02T00:00:00"
    assert params["orderby"] == "date"
    assert params["order"] == "asc"


@pytest.mark.parametrize(
    "found",
    [
        pytest.param([], id="nothing-published"),
        pytest.param(
            [{"slug": "hubble-sees-a-galaxy", "link": "https://science.nasa.gov/x/"}],
            id="not-an-apod",
        ),
        pytest.param(
            [
                {
                    "slug": "apod-2020-january-10-a-nebula",
                    "link": "https://science.nasa.gov/y/",
                }
            ],
            id="apod-of-another-day",
        ),
    ],
)
async def test_raises_not_found_without_an_apod_article_for_the_date(
    articles: ApodArticleClient, respx_mock: respx.MockRouter, found: list[object]
) -> None:
    respx_mock.get(ARTICLES_URL).respond(200, json=found)

    with pytest.raises(ApodNotFoundError):
        await articles.get_entry(BETELGEUSE_DATE)


async def test_takes_the_first_apod_article_of_the_day(
    articles: ApodArticleClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.get(ARTICLES_URL).respond(
        200,
        json=[
            {
                "slug": "apod-2020-january-1-betelgeuse-imagined",
                "link": BETELGEUSE_ARTICLE_URL,
            },
            {
                "slug": "apod-2020-january-1-a-repost",
                "link": "https://science.nasa.gov/z/",
            },
        ],
    )
    respx_mock.get(BETELGEUSE_ARTICLE_URL).respond(
        200, text=read_fixture("article_image.html")
    )

    entry = await articles.get_entry(BETELGEUSE_DATE)

    assert entry.title == "Betelgeuse Imagined"


@pytest.mark.parametrize(
    ("response", "error"),
    [
        pytest.param(httpx.Response(404), "Article search returned 404", id="no-route"),
        pytest.param(
            httpx.Response(200, json={"code": "rest_disabled"}),
            "unexpected data",
            id="not-a-list",
        ),
    ],
)
async def test_raises_bad_response_when_the_search_breaks(
    articles: ApodArticleClient,
    respx_mock: respx.MockRouter,
    response: httpx.Response,
    error: str,
) -> None:
    respx_mock.get(ARTICLES_URL).mock(return_value=response)

    with pytest.raises(ApodBadResponseError, match=error):
        await articles.get_entry(BETELGEUSE_DATE)


async def test_raises_bad_response_when_article_page_is_missing(
    articles: ApodArticleClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.get(ARTICLES_URL).respond(
        200, text=read_fixture("wp_image_articles.json")
    )
    respx_mock.get(BETELGEUSE_ARTICLE_URL).respond(404)

    with pytest.raises(ApodBadResponseError, match="Article page returned 404"):
        await articles.get_entry(BETELGEUSE_DATE)
