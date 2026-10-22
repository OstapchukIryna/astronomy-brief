import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.exc import InterfaceError, OperationalError

from app.api.errors import register_exception_handlers
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from app.domain.dates import InvalidApodDateError
from app.domain.history import InvalidHistoryFilterError
from app.domain.llm import LlmBadResponseError, LlmUnavailableError


def app_raising(error: Exception) -> FastAPI:
    """An app with our error handlers and one route that raises the given error."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/fails")
    async def fails() -> None:
        raise error

    return app


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        pytest.param(
            ApodNotFoundError("No article for 2020-01-01"),
            404,
            "There is no APOD for this date. Today's picture may not be published yet.",
            id="apod-not-found",
        ),
        pytest.param(
            ApodUnavailableError("API request failed"),
            503,
            "NASA is not available right now. Try again later.",
            id="apod-unavailable",
        ),
        pytest.param(
            ApodBadResponseError("placeholder data"),
            502,
            "NASA returned data we couldn't use.",
            id="apod-bad-response",
        ),
        pytest.param(
            LlmUnavailableError("LLM request failed"),
            503,
            "The language model is not available right now. Try again later.",
            id="llm-unavailable",
        ),
        pytest.param(
            LlmBadResponseError("empty answer"),
            502,
            "The language model returned an answer we couldn't use.",
            id="llm-bad-response",
        ),
        pytest.param(
            OperationalError("SELECT 1", {}, ConnectionRefusedError("refused")),
            503,
            "The database is not available right now. Try again later.",
            id="database-operational",
        ),
        pytest.param(
            InterfaceError("SELECT 1", {}, ConnectionRefusedError("refused")),
            503,
            "The database is not available right now. Try again later.",
            id="database-interface",
        ),
        pytest.param(
            InvalidApodDateError("The date must not be in the future"),
            400,
            "The date must not be in the future",
            id="invalid-date",
        ),
        pytest.param(
            InvalidHistoryFilterError("The start date is after the end date"),
            400,
            "The start date is after the end date",
            id="invalid-history-filter",
        ),
    ],
)
async def test_maps_each_error_to_its_status_and_detail(
    error: Exception, expected_status: int, expected_detail: str
) -> None:
    transport = httpx.ASGITransport(app=app_raising(error))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/fails")

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
