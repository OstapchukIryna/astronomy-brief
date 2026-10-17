import datetime as dt
from typing import Any

from fastapi import APIRouter, status

from app.api.dependencies import BriefServiceDep
from app.schemas.brief import BriefResponse, ExplanationResponse, FactsResponse
from app.schemas.error import ErrorResponse

router = APIRouter(prefix="/briefs", tags=["briefs"])


Responses = dict[int | str, dict[str, Any]]

_APOD_RESPONSES: Responses = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "The date is before 1995-06-16 or in the future",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "There is no APOD for this date",
    },
    status.HTTP_502_BAD_GATEWAY: {
        "model": ErrorResponse,
        "description": "NASA returned data we couldn't use",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "NASA is unavailable, try again later",
    },
}

_GENERATED_RESPONSES: Responses = {
    **_APOD_RESPONSES,
    status.HTTP_502_BAD_GATEWAY: {
        "model": ErrorResponse,
        "description": "NASA or the language model returned data we couldn't use",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "NASA or the language model is unavailable, try again later",
    },
}


@router.get("/{date}", responses=_APOD_RESPONSES)
async def get_brief(date: dt.date, service: BriefServiceDep) -> BriefResponse:
    """Return the APOD brief for the given date. The date must be between 1995-06-16 and today in US Eastern time."""
    brief = await service.get_or_create(date)
    return BriefResponse.model_validate(brief)


@router.get("/{date}/explanation", responses=_GENERATED_RESPONSES)
async def get_explanation(
    date: dt.date, service: BriefServiceDep
) -> ExplanationResponse:
    """Return a beginner-friendly explanation of the APOD, based only on NASA's text.

    Is generated on the first request and then pulled out from the database.
    """
    explanation = await service.get_explanation(date)
    return ExplanationResponse(date=date, explanation=explanation)


@router.get("/{date}/facts", responses=_GENERATED_RESPONSES)
async def get_facts(date: dt.date, service: BriefServiceDep) -> FactsResponse:
    """Return 3 to 5 interesting facts about the APOD's topic.

    Is generated on the first request and then pulled out from the database.
    """
    facts = await service.get_facts(date)
    return FactsResponse(date=date, facts=facts)
