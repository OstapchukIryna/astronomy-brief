import datetime as dt
import json
from collections.abc import AsyncIterator, Callable

import httpx
import pytest
import respx

from app.clients.apod.nasa_api import NASA_API_URL, ApodApiClient
from app.domain.apod import ApodBadResponseError, ApodUnavailableError, MediaType

BETELGEUSE_DATE = dt.date(2020, 1, 1)
VALID_URL = "https://assets.science.nasa.gov/content/dam/science/cds/apod/apod/2020/january/BetelgeuseImagined_EsoCalcada_2662.jpg"


@pytest.fixture
async def nasa_api() -> AsyncIterator[ApodApiClient]:
    async with httpx.AsyncClient() as http:
        yield ApodApiClient(http, api_key="test-key")


async def test_maps_response_to_entry(
    nasa_api: ApodApiClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.get(NASA_API_URL).respond(
        200, json=json.loads(read_fixture("nasa_api_valid.json"))
    )

    entry = await nasa_api.get_entry(BETELGEUSE_DATE)

    assert entry.date == BETELGEUSE_DATE
    assert entry.title == "Betelgeuse Imagined"
    assert entry.media_type == MediaType.IMAGE
    assert entry.url == VALID_URL
    assert entry.hd_url == VALID_URL
    assert entry.credit == "ESO, L. Calcada"


async def test_sends_date_and_api_key(
    nasa_api: ApodApiClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    route = respx_mock.get(NASA_API_URL).respond(
        200, json=json.loads(read_fixture("nasa_api_valid.json"))
    )

    await nasa_api.get_entry(BETELGEUSE_DATE)

    params = route.calls.last.request.url.params
    assert params["date"] == "2020-01-01"
    assert params["api_key"] == "test-key"


async def test_rejects_placeholder_response(
    nasa_api: ApodApiClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.get(NASA_API_URL).respond(
        200, json=json.loads(read_fixture("nasa_api_placeholder.json"))
    )

    with pytest.raises(ApodBadResponseError, match="placeholder"):
        await nasa_api.get_entry(BETELGEUSE_DATE)


@pytest.mark.parametrize(
    ("status", "body_fixture", "expected_error"),
    [
        pytest.param(
            400, "nasa_api_error_400.json", ApodBadResponseError, id="date-out-of-range"
        ),
        pytest.param(
            403, "nasa_api_error_403.json", ApodBadResponseError, id="invalid-key"
        ),
        pytest.param(429, None, ApodUnavailableError, id="rate-limited"),
        pytest.param(503, None, ApodUnavailableError, id="server-error"),
    ],
)
async def test_maps_error_status(
    nasa_api: ApodApiClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
    status: int,
    body_fixture: str | None,
    expected_error: type[Exception],
) -> None:
    body = json.loads(read_fixture(body_fixture)) if body_fixture else None
    respx_mock.get(NASA_API_URL).respond(status, json=body)

    with pytest.raises(expected_error):
        await nasa_api.get_entry(BETELGEUSE_DATE)
