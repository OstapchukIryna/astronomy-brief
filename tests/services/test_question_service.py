import datetime as dt
from dataclasses import replace

import pytest

from app.domain.apod import (
    ApodBadResponseError,
    ApodEntry,
    ApodNotFoundError,
    ApodSource,
    ApodUnavailableError,
)
from app.domain.brief import Brief
from app.domain.dates import InvalidApodDateError
from app.domain.llm import LlmBadResponseError, LlmUnavailableError, QuestionLlm
from app.domain.question import OffTopicQuestionError, Question
from app.services.entries import EntryStore
from app.services.question import QuestionService
from tests.fakes import DATE, ENTRY, FACTS, FakeLlm, FakeSource, FakeUnitOfWork

QUESTION = Question("Why is Betelgeuse fading?")


def make_service(
    uow: FakeUnitOfWork | None = None,
    source: ApodSource | None = None,
    llm: QuestionLlm | None = None,
) -> QuestionService:
    uow = uow or FakeUnitOfWork()
    return QuestionService(EntryStore(uow, source or FakeSource()), llm or FakeLlm())


async def uow_store(entry: ApodEntry) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.briefs.insert_if_absent(entry)
    return uow


async def test_answers_an_on_topic_question() -> None:
    llm = FakeLlm(on_topic=True, answer="It is losing brightness.")

    answer = await make_service(await uow_store(ENTRY), llm=llm).ask(DATE, QUESTION)

    assert answer == "It is losing brightness."


async def test_refuses_an_off_topic_question_without_paying_for_an_answer() -> None:
    llm = FakeLlm(on_topic=False)

    with pytest.raises(
        OffTopicQuestionError, match="must be about the picture of the day"
    ):
        await make_service(await uow_store(ENTRY), llm=llm).ask(DATE, QUESTION)

    assert llm.answered == []


async def test_fetches_and_stores_a_missing_entry_but_not_the_answer() -> None:
    uow = FakeUnitOfWork()
    llm = FakeLlm(answer="It is losing brightness.")

    answer = await make_service(uow, source=FakeSource(ENTRY), llm=llm).ask(
        DATE, QUESTION
    )

    assert answer == "It is losing brightness."
    assert await uow.briefs.get_by_date(DATE) == Brief(entry=ENTRY)


async def test_leaves_a_stored_brief_unchanged() -> None:
    uow = await uow_store(ENTRY)
    await uow.briefs.set_explanation_if_absent(DATE, "A star is fading.")
    await uow.briefs.set_facts_if_absent(DATE, FACTS)
    source = FakeSource(ENTRY)

    await make_service(uow, source=source).ask(DATE, QUESTION)

    assert source.calls == 0
    assert await uow.briefs.get_by_date(DATE) == Brief(
        entry=ENTRY, simple_explanation="A star is fading.", facts=FACTS
    )


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(LlmUnavailableError("LLM request failed"), id="unavailable"),
        pytest.param(LlmBadResponseError("not a boolean"), id="bad-response"),
    ],
)
async def test_classifier_errors_reach_the_caller_and_keep_the_entry(
    error: Exception,
) -> None:
    uow = FakeUnitOfWork()
    llm = FakeLlm(on_topic=error)

    with pytest.raises(type(error)):
        await make_service(uow, source=FakeSource(ENTRY), llm=llm).ask(DATE, QUESTION)

    assert len(llm.classified) == 1
    assert llm.answered == []
    assert await uow.briefs.get_by_date(DATE) == Brief(entry=ENTRY)


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(LlmUnavailableError("LLM request failed"), id="unavailable"),
        pytest.param(LlmBadResponseError("empty answer"), id="bad-response"),
    ],
)
async def test_answer_errors_reach_the_caller_without_a_retry(error: Exception) -> None:
    llm = FakeLlm(answer=error)

    with pytest.raises(type(error)):
        await make_service(await uow_store(ENTRY), llm=llm).ask(DATE, QUESTION)

    assert len(llm.answered) == 1


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ApodNotFoundError("No article"), id="not-found"),
        pytest.param(ApodUnavailableError("API request failed"), id="unavailable"),
        pytest.param(ApodBadResponseError("placeholder data"), id="bad-response"),
    ],
)
async def test_nasa_errors_stop_before_the_llm(error: Exception) -> None:
    uow = FakeUnitOfWork()
    llm = FakeLlm()

    with pytest.raises(type(error)):
        await make_service(uow, source=FakeSource(error), llm=llm).ask(DATE, QUESTION)

    assert llm.classified == []
    assert await uow.briefs.get_by_date(DATE) is None


@pytest.mark.parametrize(
    "date",
    [
        pytest.param(dt.date(1995, 6, 15), id="before-the-first-apod"),
        pytest.param(dt.date(2100, 1, 1), id="future"),
    ],
)
async def test_rejects_dates_without_an_apod_before_any_call(date: dt.date) -> None:
    source = FakeSource(ENTRY)
    llm = FakeLlm()

    with pytest.raises(InvalidApodDateError):
        await make_service(source=source, llm=llm).ask(date, QUESTION)

    assert source.calls == 0
    assert llm.classified == []


async def test_answers_for_the_first_apod_date() -> None:
    first_entry = replace(ENTRY, date=dt.date(1995, 6, 16))
    llm = FakeLlm(answer="It is losing brightness.")

    answer = await make_service(source=FakeSource(first_entry), llm=llm).ask(
        dt.date(1995, 6, 16), QUESTION
    )

    assert answer == "It is losing brightness."


class OutsideTransactionLlm(FakeLlm):
    """Fails the test if the classifier or the answer is called inside a transaction."""

    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__()
        self._uow = uow

    async def is_on_topic(self, entry: ApodEntry, question: Question) -> bool:
        assert not self._uow.in_transaction, "Classifier called inside a transaction"
        return await super().is_on_topic(entry, question)

    async def answer(self, entry: ApodEntry, question: Question) -> str:
        assert not self._uow.in_transaction, "Answer called inside a transaction"
        return await super().answer(entry, question)


async def test_calls_the_llm_outside_a_transaction() -> None:
    uow = FakeUnitOfWork()
    llm = OutsideTransactionLlm(uow)

    await make_service(uow, source=FakeSource(ENTRY), llm=llm).ask(DATE, QUESTION)

    assert len(llm.answered) == 1


class NumberedAnswersLlm(FakeLlm):
    """Answers "Answer 1.", "Answer 2.", ..."""

    async def answer(self, entry: ApodEntry, question: Question) -> str:
        await super().answer(entry, question)
        return f"Answer {len(self.answered)}."


async def test_answers_the_same_question_anew_each_time() -> None:
    service = make_service(await uow_store(ENTRY), llm=NumberedAnswersLlm())

    first = await service.ask(DATE, QUESTION)
    second = await service.ask(DATE, QUESTION)

    assert (first, second) == ("Answer 1.", "Answer 2.")


async def test_both_calls_get_the_stored_entry_and_the_question() -> None:
    stored = replace(ENTRY, title="Betelgeuse, as stored")
    source = FakeSource(replace(ENTRY, title="Betelgeuse, from NASA"))
    llm = FakeLlm()

    await make_service(await uow_store(stored), source=source, llm=llm).ask(
        DATE, QUESTION
    )

    assert llm.classified == [(stored, QUESTION)]
    assert llm.answered == [(stored, QUESTION)]
