from typing import Annotated

from fastapi import Depends, Request

from app.database import Database, get_database
from app.domain.apod import ApodSource
from app.domain.llm import LlmClient
from app.domain.unit_of_work import UnitOfWork
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.brief import BriefService


def get_apod_source(request: Request) -> ApodSource:
    return request.app.state.apod_source


def get_llm(request: Request) -> LlmClient:
    return request.app.state.llm


def get_unit_of_work(db: Annotated[Database, Depends(get_database)]) -> UnitOfWork:
    return SqlUnitOfWork(db.sessionmaker)


def get_brief_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    source: Annotated[ApodSource, Depends(get_apod_source)],
    llm: Annotated[LlmClient, Depends(get_llm)],
) -> BriefService:
    return BriefService(uow, source, llm)


BriefServiceDep = Annotated[BriefService, Depends(get_brief_service)]
