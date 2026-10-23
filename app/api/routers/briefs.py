import datetime as dt

from fastapi import APIRouter

from app import views
from app.api.dependencies import BriefServiceDep, SessionFactoryDep
from app.api.errors import DATABASE_ERRORS, error_responses
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from app.domain.dates import InvalidApodDateError
from app.domain.history import HistoryFilter, InvalidHistoryFilterError, PageRequest
from app.domain.llm import LlmBadResponseError, LlmUnavailableError
from app.schemas.brief import (
    BriefResponse,
    BriefSummaryResponse,
    ExplanationResponse,
    FactsResponse,
    HistoryResponse,
)

router = APIRouter(prefix="/briefs", tags=["briefs"])

_HISTORY_ERRORS = (InvalidHistoryFilterError, *DATABASE_ERRORS)
_ENTRY_ERRORS = (
    InvalidApodDateError,
    ApodNotFoundError,
    ApodBadResponseError,
    ApodUnavailableError,
    *DATABASE_ERRORS,
)
_GENERATED_ERRORS = (*_ENTRY_ERRORS, LlmBadResponseError, LlmUnavailableError)

DEFAULT_PAGE_SIZE = 20


@router.get("", responses=error_responses(*_HISTORY_ERRORS))
async def list_history(
    session_factory: SessionFactoryDep,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    keyword: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    before: dt.date | None = None,
) -> HistoryResponse:
    """Return stored briefs with the newest first.

    Only briefs that someone has already requested are stored.
    """
    page = await views.list_history(
        session_factory,
        HistoryFilter(date_from=date_from, date_to=date_to, keyword=keyword),
        PageRequest(limit=limit, before=before),
    )
    return HistoryResponse(
        items=[BriefSummaryResponse.model_validate(item) for item in page.items],
        next_before=page.next_before,
    )


@router.get("/{date}", responses=error_responses(*_ENTRY_ERRORS))
async def get_brief(date: dt.date, service: BriefServiceDep) -> BriefResponse:
    """Return the APOD brief for the given date. The date must be between 1995-06-16 and today in US Eastern time."""
    entry = await service.get_entry(date)
    return BriefResponse.model_validate(entry)


@router.get("/{date}/explanation", responses=error_responses(*_GENERATED_ERRORS))
async def get_explanation(
    date: dt.date, service: BriefServiceDep
) -> ExplanationResponse:
    """Return a beginner-friendly explanation of the APOD, based only on NASA's text.

    Is generated on the first request and then pulled out from the database.
    """
    explanation = await service.get_explanation(date)
    return ExplanationResponse(date=date, explanation=explanation)


@router.get("/{date}/facts", responses=error_responses(*_GENERATED_ERRORS))
async def get_facts(date: dt.date, service: BriefServiceDep) -> FactsResponse:
    """Return interesting facts about the APOD's topic.

    Is generated on the first request and then pulled out from the database.
    """
    facts = await service.get_facts(date)
    return FactsResponse(date=date, facts=list(facts.items))
