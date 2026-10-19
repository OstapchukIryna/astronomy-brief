import httpx
import pytest
import respx

from app.clients.http import send

URL = "https://service.test/thing"


class Unavailable(Exception):
    pass


class BadResponse(Exception):
    pass


async def call(http: httpx.AsyncClient) -> httpx.Response:
    return await send(
        lambda: http.get(URL),
        what="Service",
        unavailable=Unavailable,
        bad_response=BadResponse,
        detail=lambda response: f": {response.text}" if response.text else "",
    )


@pytest.mark.parametrize(
    ("side_effect", "expected"),
    [
        pytest.param(httpx.ConnectError("refused"), Unavailable, id="connect-error"),
        pytest.param(httpx.ReadTimeout("slow"), Unavailable, id="timeout"),
        pytest.param(
            httpx.TooManyRedirects("loop"), BadResponse, id="too-many-redirects"
        ),
        pytest.param(
            httpx.DecodingError("broken gzip"), BadResponse, id="decoding-error"
        ),
    ],
)
async def test_request_errors_become_unavailable_or_bad_response(
    http: httpx.AsyncClient,
    respx_mock: respx.MockRouter,
    side_effect: httpx.RequestError,
    expected: type[Exception],
) -> None:
    respx_mock.get(URL).mock(side_effect=side_effect)

    with pytest.raises(
        expected, match=f"Service failed: {type(side_effect).__name__}"
    ) as exc_info:
        await call(http)

    assert exc_info.value.__cause__ is side_effect


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_raises_unavailable_on_server_errors(
    http: httpx.AsyncClient, respx_mock: respx.MockRouter, status: int
) -> None:
    respx_mock.get(URL).respond(status, text="overloaded")

    with pytest.raises(Unavailable, match=f"Service returned {status}: overloaded"):
        await call(http)


@pytest.mark.parametrize("status", [200, 301, 404])
async def test_returns_other_responses(
    http: httpx.AsyncClient, respx_mock: respx.MockRouter, status: int
) -> None:
    respx_mock.get(URL).respond(status)

    response = await call(http)

    assert response.status_code == status
