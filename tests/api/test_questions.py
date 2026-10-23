import datetime as dt
import logging
from dataclasses import replace

import httpx
import pytest
from fastapi import status

from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodUnavailableError,
)
from app.domain.brief import Brief
from app.domain.llm import LlmBadResponseError, LlmUnavailableError
from app.repositories.unit_of_work import SqlUnitOfWork
from tests.api.conftest import UseFakes
from tests.fakes import DATE, ENTRY, FakeLlm, FakeSource

QUESTION_RULE = (
    "The question must be 3 to 300 characters long, without control characters."
)
OFF_TOPIC = "The question must be about the picture of the day."


async def ask(
    client: httpx.AsyncClient, question: object, date: str = "2020-01-01"
) -> httpx.Response:
    return await client.post("/questions", json={"date": date, "question": question})


async def test_answers_on_topic_question(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(
        FakeSource(ENTRY), llm=FakeLlm(on_topic=True, answer="It is losing brightness.")
    )

    response = await ask(client, "Why is Betelgeuse fading?")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "date": "2020-01-01",
        "answer": "It is losing brightness.",
    }


@pytest.mark.parametrize(
    "question",
    [
        pytest.param("ab", id="2-characters"),
        pytest.param("  ab  ", id="short-after-trimming"),
        pytest.param("   ", id="whitespace-only"),
        pytest.param("a" * 301, id="301-characters"),
        pytest.param("a" * 1_000_000, id="huge"),
        pytest.param("Why\x00is it red?", id="control-character"),
    ],
)
async def test_rejects_a_question_that_breaks_the_rule(
    client: httpx.AsyncClient, use_fakes: UseFakes, question: str
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await ask(client, question)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": QUESTION_RULE}


@pytest.mark.parametrize(
    "question",
    [
        pytest.param("abc", id="3-characters"),
        pytest.param("a" * 300, id="300-characters"),
    ],
)
async def test_accepts_questions_at_the_limits(
    client: httpx.AsyncClient, use_fakes: UseFakes, question: str
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await ask(client, question)

    assert response.status_code == status.HTTP_200_OK


async def test_refuses_off_topic_question(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(ENTRY), llm=FakeLlm(on_topic=False))

    response = await ask(client, "What is the best pizza in Kyiv?")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": OFF_TOPIC}


@pytest.mark.parametrize(
    "date",
    [
        pytest.param("1995-06-15", id="before-the-first-apod"),
        pytest.param("2100-01-01", id="future"),
    ],
)
async def test_rejects_a_date_without_an_apod(
    client: httpx.AsyncClient, use_fakes: UseFakes, date: str
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await ask(client, "Why is Betelgeuse fading?", date=date)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_answers_for_the_first_apod_date(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(replace(ENTRY, date=dt.date(1995, 6, 16))))

    response = await ask(client, "Why is Betelgeuse fading?", date="1995-06-16")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="empty"),
        pytest.param({"date": "2020-01-01"}, id="no-question"),
        pytest.param({"question": "Why is it red?"}, id="no-date"),
        pytest.param(
            {"date": "2026-13-01", "question": "Why is it red?"}, id="impossible-date"
        ),
        pytest.param(
            {"date": "2026/10/10", "question": "Why is it red?"}, id="wrong-date-format"
        ),
        pytest.param({"date": "2020-01-01", "question": None}, id="null-question"),
        pytest.param({"date": "2020-01-01", "question": 123}, id="number-question"),
    ],
)
async def test_rejects_a_malformed_body_with_422(
    client: httpx.AsyncClient, use_fakes: UseFakes, body: dict[str, object]
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await client.post("/questions", json=body)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_rejects_a_body_that_is_not_a_json(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await client.post(
        "/questions", content="not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    ("source", "llm", "expected_status", "expected_detail"),
    [
        pytest.param(
            FakeSource(ApodNotFoundError("No article for 2020-01-01")),
            FakeLlm(),
            404,
            "There is no APOD for this date. Today's picture may not be published yet.",
            id="nasa-not-found",
        ),
        pytest.param(
            FakeSource(ApodUnavailableError("https://api.nasa.gov returned 503")),
            FakeLlm(),
            503,
            "NASA is not available right now. Try again later.",
            id="nasa-unavailable",
        ),
        pytest.param(
            FakeSource(ApodBadResponseError("placeholder data")),
            FakeLlm(),
            502,
            "NASA returned data we couldn't use.",
            id="nasa-bad-response",
        ),
        pytest.param(
            FakeSource(ENTRY),
            FakeLlm(on_topic=LlmUnavailableError("LLM request failed")),
            503,
            "The language model is not available right now. Try again later.",
            id="classifier-unavailable",
        ),
        pytest.param(
            FakeSource(ENTRY),
            FakeLlm(answer=LlmBadResponseError("internal: empty choices")),
            502,
            "The language model returned an answer we couldn't use.",
            id="answer-bad-response",
        ),
    ],
)
async def test_maps_source_and_llm_errors_without_internal_details(
    client: httpx.AsyncClient,
    use_fakes: UseFakes,
    source: FakeSource,
    llm: FakeLlm,
    expected_status: int,
    expected_detail: str,
) -> None:
    use_fakes(source, llm=llm)

    response = await ask(client, "Why is Betelgeuse fading?")

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


async def test_checks_the_question_before_calling_nasa(
    client: httpx.AsyncClient, use_fakes: UseFakes, uow: SqlUnitOfWork
) -> None:
    source = FakeSource(ApodUnavailableError("API request failed"))
    use_fakes(source)

    response = await ask(client, "ab")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert source.calls == 0
    async with uow:
        assert await uow.briefs.get_by_date(DATE) is None


async def test_keeps_the_fetched_entry_when_the_llm_fails(
    client: httpx.AsyncClient, use_fakes: UseFakes, uow: SqlUnitOfWork
) -> None:
    use_fakes(
        FakeSource(ENTRY),
        llm=FakeLlm(on_topic=LlmUnavailableError("LLM request failed")),
    )

    response = await ask(client, "Why is Betelgeuse fading?")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    async with uow:
        assert await uow.briefs.get_by_date(DATE) == Brief(entry=ENTRY)


SENTINEL = "Is the sentinel 7f3a visible?"


@pytest.mark.parametrize(
    "llm",
    [
        pytest.param(FakeLlm(), id="answered"),
        pytest.param(FakeLlm(on_topic=False), id="off-topic"),
        pytest.param(
            FakeLlm(on_topic=LlmUnavailableError("LLM request failed")),
            id="classifier-fails",
        ),
        pytest.param(
            FakeLlm(answer=LlmBadResponseError("LLM returned 400")), id="answer-fails"
        ),
    ],
)
async def test_never_logs_the_question(
    client: httpx.AsyncClient,
    use_fakes: UseFakes,
    caplog: pytest.LogCaptureFixture,
    llm: FakeLlm,
) -> None:
    use_fakes(FakeSource(ENTRY), llm=llm)
    caplog.set_level(logging.DEBUG)

    await ask(client, SENTINEL)
