from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_apod_source, get_llm
from app.database import get_session
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodSource,
    ApodUnavailableError,
)
from tests.fakes import ENTRY, FakeLlm, FakeSource


@pytest.fixture
def use_source(app: FastAPI, session: AsyncSession) -> Callable[[ApodSource], None]:
    """Make the app use the test session and the given APOD source."""
    app.dependency_overrides[get_session] = lambda: session

    def _use(source: ApodSource) -> None:
        app.dependency_overrides[get_apod_source] = lambda: source
        app.dependency_overrides[get_llm] = lambda: FakeLlm()

    return _use


async def test_returns_brief_for_date(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(FakeSource(ENTRY))

    response = await client.get("/briefs/2020-01-01")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "date": "2020-01-01",
        "title": "Betelgeuse Imagined",
        "explanation": "Why is Betelgeuse fading?",
        "media_type": "image",
        "url": "https://example.com/betelgeuse.jpg",
        "hd_url": None,
        "credit": None,
    }


async def test_rejects_malformed_date(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(FakeSource(ENTRY))

    response = await client.get("/briefs/2020-13-45")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(
            ApodNotFoundError("No article for 2020-01-01"), 404, id="not-found"
        ),
        pytest.param(ApodUnavailableError("API request failed"), 503, id="unavailable"),
        pytest.param(ApodBadResponseError("placeholder data"), 502, id="bad-response"),
    ],
)
async def test_maps_source_errors_to_status(
    client: httpx.AsyncClient,
    use_source: Callable[[ApodSource], None],
    error: Exception,
    expected_status: int,
) -> None:
    use_source(FakeSource(error))

    response = await client.get("/briefs/2020-01-01")

    assert response.status_code == expected_status


async def test_does_not_expose_internal_error_details(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(
        FakeSource(
            ApodUnavailableError(
                "Archive returned 503: https://apod.nasa.gov/apod/ap200101.html"
            )
        )
    )

    response = await client.get("/briefs/2020-01-01")

    assert "apod.nasa.gov" not in response.text


async def test_rejects_future_date_without_calling_source(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    source = FakeSource(ENTRY)
    use_source(source)

    response = await client.get("/briefs/2100-01-01")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert source.calls == 0
