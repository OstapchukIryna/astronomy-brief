from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DbDep
from app.schemas.error import ErrorResponse
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/health/ready",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "The database is unreachable",
        },
    },
)
async def readiness(db: DbDep) -> HealthResponse:
    if not await db.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return HealthResponse(status="ok")
