from typing import Annotated

from fastapi import Depends, Request

from app.database import DbSession
from app.domain.apod import ApodSource
from app.domain.llm import LlmClient
from app.repositories.brief import SqlBriefRepository
from app.services.brief import BriefService


def get_apod_source(request: Request) -> ApodSource:
    return request.app.state.apod_source


def get_llm(request: Request) -> LlmClient:
    return request.app.state.llm


def get_brief_service(
    session: DbSession,
    source: Annotated[ApodSource, Depends(get_apod_source)],
    llm: Annotated[LlmClient, Depends(get_llm)],
) -> BriefService:
    return BriefService(session, SqlBriefRepository(session), source, llm)


BriefServiceDep = Annotated[BriefService, Depends(get_brief_service)]
