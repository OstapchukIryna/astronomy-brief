from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import Database, get_database

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: Annotated[Database, Depends(get_database)]) -> dict[str, str]:
    if not await db.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return {"status": "ok"}
