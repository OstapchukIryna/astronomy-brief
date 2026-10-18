import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from app.domain.dates import InvalidApodDateError
from app.domain.history import InvalidHistoryFilterError
from app.domain.llm import LlmBadResponseError, LlmUnavailableError

logger = logging.getLogger(__name__)

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]


def _external_error_handler(status_code: int, detail: str) -> Handler:
    """Build a handler that hides the internal message from the client and logs it."""

    async def handle(request: Request, error: Exception) -> JSONResponse:
        logger.warning(
            "%s failed: %s: %s", request.url.path, type(error).__name__, error
        )
        return JSONResponse(status_code=status_code, content={"detail": detail})

    return handle


async def _handle_invalid_request(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(error)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        ApodNotFoundError,
        _external_error_handler(
            status.HTTP_404_NOT_FOUND, "There is no APOD for this date."
        ),
    )
    app.add_exception_handler(
        ApodUnavailableError,
        _external_error_handler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "NASA is not available right now. Try again later.",
        ),
    )
    app.add_exception_handler(
        ApodBadResponseError,
        _external_error_handler(
            status.HTTP_502_BAD_GATEWAY, "NASA returned data we couldn't use."
        ),
    )
    app.add_exception_handler(
        LlmUnavailableError,
        _external_error_handler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The language model is not available right now. Try again later.",
        ),
    )
    app.add_exception_handler(
        LlmBadResponseError,
        _external_error_handler(
            status.HTTP_502_BAD_GATEWAY,
            "The language model returned an answer we couldn't use.",
        ),
    )

    app.add_exception_handler(InvalidApodDateError, _handle_invalid_request)
    app.add_exception_handler(InvalidHistoryFilterError, _handle_invalid_request)
