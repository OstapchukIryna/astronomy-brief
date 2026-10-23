from fastapi import APIRouter

from app.api.dependencies import QuestionServiceDep
from app.api.errors import DATABASE_ERRORS, error_responses
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from app.domain.dates import InvalidApodDateError
from app.domain.llm import LlmBadResponseError, LlmUnavailableError
from app.domain.question import InvalidQuestionError, OffTopicQuestionError, Question
from app.schemas.question import AnswerResponse, QuestionRequest

router = APIRouter(prefix="/questions", tags=["questions"])

_QUESTION_ERRORS = (
    InvalidQuestionError,
    OffTopicQuestionError,
    InvalidApodDateError,
    ApodNotFoundError,
    ApodBadResponseError,
    ApodUnavailableError,
    LlmBadResponseError,
    LlmUnavailableError,
    *DATABASE_ERRORS,
)


@router.post("", responses=error_responses(*_QUESTION_ERRORS))
async def ask_question(
    body: QuestionRequest, service: QuestionServiceDep
) -> AnswerResponse:
    """Answer a question about the APOD of the given date.

    The question must be about the picture. Answers use NASA's text and
    well-established knowledge and are not saved in database.
    """
    question = Question(body.question)
    answer = await service.ask(body.date, question)
    return AnswerResponse(date=body.date, answer=answer)
