import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from app.domain.dates import InvalidApodDateError
from app.domain.history import InvalidHistoryFilterError
from app.domain.llm import LlmBadResponseError, LlmUnavailableError
from app.domain.questions import InvalidQuestionError, OffTopicQuestionError
from app.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    """The path of error to the client or docs.

    `detail` is the friendly message for the client, while description is logged with details.
    """

    status_code: int
    description: str
    detail: str | None = None


DATABASE_UNAVAILABLE = ErrorSpec(
    status.HTTP_503_SERVICE_UNAVAILABLE,
    "The database is unavailable.",
    "The database is not available right now. Try again later.",
)

DATABASE_ERRORS = (OperationalError, InterfaceError)

ERRORS: dict[type[Exception], ErrorSpec] = {
    InvalidApodDateError: ErrorSpec(
        status.HTTP_400_BAD_REQUEST,
        "The date is before 1995-06-16 or in the future.",
    ),
    InvalidHistoryFilterError: ErrorSpec(
        status.HTTP_400_BAD_REQUEST,
        "The start date is after the end date, the keyword is not 3 to 100 "
        "characters long or contains control characters, or the page size is "
        "not 1 to 100.",
    ),
    InvalidQuestionError: ErrorSpec(
        status.HTTP_400_BAD_REQUEST,
        "The question is not 3 to 300 characters long or contains control characters.",
    ),
    OffTopicQuestionError: ErrorSpec(
        status.HTTP_400_BAD_REQUEST,
        "The question is not about the picture of the day.",
    ),
    ApodNotFoundError: ErrorSpec(
        status.HTTP_404_NOT_FOUND,
        "There is no APOD for this date, or today's is not published yet.",
        "There is no APOD for this date. Today's picture may not be published yet.",
    ),
    ApodBadResponseError: ErrorSpec(
        status.HTTP_502_BAD_GATEWAY,
        "NASA returned data we couldn't use.",
        "NASA returned data we couldn't use.",
    ),
    ApodUnavailableError: ErrorSpec(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "NASA is unavailable.",
        "NASA is not available right now. Try again later.",
    ),
    LlmBadResponseError: ErrorSpec(
        status.HTTP_502_BAD_GATEWAY,
        "The language model returned an answer we couldn't use.",
        "The language model returned an answer we couldn't use.",
    ),
    LlmUnavailableError: ErrorSpec(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "The language model is unavailable.",
        "The language model is not available right now. Try again later.",
    ),
    OperationalError: DATABASE_UNAVAILABLE,
    InterfaceError: DATABASE_UNAVAILABLE,
}


def _handler(spec: ErrorSpec) -> Handler:
    async def handle(request: Request, error: Exception) -> JSONResponse:
        if spec.detail is None:
            detail = str(error)
        else:
            logger.warning(
                "%s failed: %s: %s", request.url.path, type(error).__name__, error
            )
            detail = spec.detail
        return JSONResponse(status_code=spec.status_code, content={"detail": detail})

    return handle


def register_exception_handlers(app: FastAPI) -> None:
    for error_type, spec in ERRORS.items():
        app.add_exception_handler(error_type, _handler(spec))


Responses = dict[int | str, dict[str, Any]]


def error_responses(*error_types: type[Exception]) -> Responses:
    """Build a route's OpenAPI `responses` from the errors of the route.

    If the errors are with the same status, their descriptions wil be joined.
    """
    descriptions: dict[int, list[str]] = {}
    for error_type in error_types:
        spec = ERRORS[error_type]
        descriptions.setdefault(spec.status_code, []).append(spec.description)
    return {
        code: {"model": ErrorResponse, "description": " ".join(dict.fromkeys(texts))}
        for code, texts in sorted(descriptions.items())
    }
