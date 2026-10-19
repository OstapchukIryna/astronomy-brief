from typing import Annotated

from fastapi import Depends, Request

from app.bootstrap import Container
from app.database import Database
from app.domain.apod import ApodSource
from app.domain.llm import LlmClient
from app.domain.unit_of_work import UnitOfWork
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.brief import BriefService


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_database(container: ContainerDep) -> Database:
    return container.db


DbDep = Annotated[Database, Depends(get_database)]


def get_apod_source(container: ContainerDep) -> ApodSource:
    return container.apod_source


def get_llm(container: ContainerDep) -> LlmClient:
    return container.llm


def get_unit_of_work(db: DbDep) -> UnitOfWork:
    return SqlUnitOfWork(db.sessionmaker)


def get_brief_service(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    source: Annotated[ApodSource, Depends(get_apod_source)],
    llm: Annotated[LlmClient, Depends(get_llm)],
) -> BriefService:
    return BriefService(uow, source, llm)


BriefServiceDep = Annotated[BriefService, Depends(get_brief_service)]
