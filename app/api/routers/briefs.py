import datetime as dt

from fastapi import APIRouter, status

from app.api.dependencies import BriefServiceDep
from app.schemas.brief import BriefResponse
from app.schemas.error import ErrorResponse

router = APIRouter(prefix="/briefs", tags=["briefs"])


@router.get(
    "/{date}",
    responses={
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
    },
)
async def get_brief(date: dt.date, service: BriefServiceDep) -> BriefResponse:
    """Return the APOD brief for the given date. The date must be between 1995-06-16 and today in US Eastern time."""
    brief = await service.get_or_create(date)
    return BriefResponse.model_validate(brief)
