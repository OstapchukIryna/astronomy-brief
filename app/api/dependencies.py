from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap import Container
from app.database import Database
from app.domain.apod import ApodSource
from app.domain.llm import LlmClient
from app.domain.unit_of_work import UnitOfWork
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.brief import BriefService
from app.services.entries import EntryStore
from app.services.question import QuestionService


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_database(container: ContainerDep) -> Database:
    return container.db


DbDep = Annotated[Database, Depends(get_database)]


def get_session_factory(db: DbDep) -> async_sessionmaker[AsyncSession]:
    return db.sessionmaker


SessionFactoryDep = Annotated[
    async_sessionmaker[AsyncSession], Depends(get_session_factory)
]


def get_unit_of_work(session_factory: SessionFactoryDep) -> UnitOfWork:
    return SqlUnitOfWork(session_factory)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_apod_source(container: ContainerDep) -> ApodSource:
    return container.apod_source


def get_llm(container: ContainerDep) -> LlmClient:
    return container.llm


def get_entry_store(
    uow: UnitOfWorkDep,
    source: Annotated[ApodSource, Depends(get_apod_source)],
) -> EntryStore:
    return EntryStore(uow, source)


def get_question_service(
    entries: Annotated[EntryStore, Depends(get_entry_store)],
    llm: Annotated[LlmClient, Depends(get_llm)],
) -> QuestionService:
    return QuestionService(entries, llm)


QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]


def get_brief_service(
    uow: UnitOfWorkDep,
    entries: Annotated[EntryStore, Depends(get_entry_store)],
    llm: Annotated[LlmClient, Depends(get_llm)],
) -> BriefService:
    return BriefService(uow, entries, llm)


BriefServiceDep = Annotated[BriefService, Depends(get_brief_service)]
