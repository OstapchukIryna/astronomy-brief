from typing import Annotated

from fastapi import Depends, Request

from app.database import DbSession
from app.domain.apod import ApodSource
from app.services.brief import BriefService


def get_apod_source(request: Request) -> ApodSource:
    return request.app.state.apod_source


def get_brief_service(
    session: DbSession,
    source: Annotated[ApodSource, Depends(get_apod_source)],
) -> BriefService:
    return BriefService(session, source)


BriefServiceDep = Annotated[BriefService, Depends(get_brief_service)]
