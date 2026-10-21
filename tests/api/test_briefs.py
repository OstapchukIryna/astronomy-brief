import datetime as dt
from dataclasses import replace
from typing import Protocol, Self

import httpx
import pytest
from fastapi import FastAPI, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_container, get_session_factory, get_unit_of_work
from app.bootstrap import Container
from app.database import Database
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodSource,
    ApodUnavailableError,
)
from app.domain.facts import Facts
from app.domain.llm import LlmBadResponseError, LlmClient, LlmUnavailableError
from app.repositories.unit_of_work import SqlUnitOfWork
from tests.fakes import ENTRY, FakeLlm, FakeSource


class UseFakes(Protocol):
    def __call__(self, source: ApodSource, llm: LlmClient | None = None) -> None: ...


class BrokenUnitOfWork:
    """A unit of work with which database can't be reached."""

    async def __aenter__(self) -> Self:
        raise OperationalError("SELECT 1", {}, ConnectionRefusedError("refused"))

    async def __aexit__(self, *args: object) -> None:
        pass  # pragma: no cover


@pytest.fixture
def use_fakes(
    app: FastAPI, session_factory: async_sessionmaker[AsyncSession], database: Database
) -> UseFakes:
    """Make the app use the test unit of work and the given APOD source."""
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    def _use(source: ApodSource, llm: LlmClient | None = None) -> None:
        container = Container(db=database, apod_source=source, llm=llm or FakeLlm())
        app.dependency_overrides[get_container] = lambda: container

    return _use


async def store_briefs(uow: SqlUnitOfWork, *days: int) -> None:
    """Save briefs for the given days of January 2020."""
    async with uow:
        for day in days:
            await uow.briefs.insert_if_absent(
                replace(ENTRY, date=dt.date(2020, 1, day))
            )
        await uow.commit()


async def test_returns_brief_for_date(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await client.get("/briefs/2020-01-01")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "date": "2020-01-01",
        "title": "Betelgeuse Imagined",
        "explanation": "Why is Betelgeuse fading?",
        "media_type": "image",
        "url": "https://example.com/betelgeuse.jpg",
        "hd_url": None,
        "credit": None,
    }


async def test_rejects_malformed_date(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(ENTRY))

    response = await client.get("/briefs/2020-13-45")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(
            ApodNotFoundError("No article for 2020-01-01"), 404, id="not-found"
        ),
        pytest.param(ApodUnavailableError("API request failed"), 503, id="unavailable"),
        pytest.param(ApodBadResponseError("placeholder data"), 502, id="bad-response"),
    ],
)
async def test_maps_source_errors_to_status(
    client: httpx.AsyncClient,
    use_fakes: UseFakes,
    error: Exception,
    expected_status: int,
) -> None:
    use_fakes(FakeSource(error))

    response = await client.get("/briefs/2020-01-01")

    assert response.status_code == expected_status


async def test_does_not_expose_internal_error_details(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(
        FakeSource(
            ApodUnavailableError(
                "Article request https://science.nasa.gov/image-article/... returned 503"
            )
        )
    )

    response = await client.get("/briefs/2020-01-01")

    assert "science.nasa.gov" not in response.text


async def test_returns_503_when_the_database_is_down(
    app: FastAPI, client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(ENTRY))
    app.dependency_overrides[get_unit_of_work] = BrokenUnitOfWork

    response = await client.get("/briefs/2020-01-01")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == (
        "The database is not available right now. Try again later."
    )


async def test_rejects_future_date(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    source = FakeSource(ENTRY)
    use_fakes(source)

    response = await client.get("/briefs/2100-01-01")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_returns_explanation_for_date(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource(), llm=FakeLlm(explanation="A star is fading."))

    response = await client.get("/briefs/2020-01-01/explanation")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"date": "2020-01-01", "explanation": "A star is fading."}


async def test_returns_facts_for_date(
    client: httpx.AsyncClient,
    use_fakes: UseFakes,
) -> None:
    use_fakes(
        FakeSource(),
        llm=FakeLlm(facts=Facts(("It is red.", "It is fading.", "It is far."))),
    )

    response = await client.get("/briefs/2020-01-01/facts")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "date": "2020-01-01",
        "facts": ["It is red.", "It is fading.", "It is far."],
    }


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/briefs/2020-01-01/explanation", id="explanation"),
        pytest.param("/briefs/2020-01-01/facts", id="facts"),
    ],
)
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(LlmUnavailableError("LLM request failed"), 503, id="unavailable"),
        pytest.param(LlmBadResponseError("empty answer"), 502, id="bad-response"),
    ],
)
async def test_maps_llm_errors_to_status(
    client: httpx.AsyncClient,
    use_fakes: UseFakes,
    path: str,
    error: Exception,
    expected_status: int,
) -> None:
    use_fakes(FakeSource(), llm=FakeLlm(explanation=error, facts=error))

    response = await client.get(path)

    assert response.status_code == expected_status


# history


async def test_history_returns_stored_briefs_newest_first(
    client: httpx.AsyncClient, uow: SqlUnitOfWork, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource())
    await store_briefs(uow, 1, 2, 3)

    response = await client.get("/briefs", params={"limit": 2})

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert [item["date"] for item in body["items"]] == ["2020-01-03", "2020-01-02"]
    assert body["items"][0] == {
        "date": "2020-01-03",
        "title": "Betelgeuse Imagined",
        "media_type": "image",
        "url": "https://example.com/betelgeuse.jpg",
    }
    assert body["next_before"] == "2020-01-02"


async def test_history_rejects_invalid_request(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource())

    response = await client.get(
        "/briefs", params={"date_from": "2020-01-02", "date_to": "2020-01-01"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_history_pages_through_all_briefs_by_date(
    client: httpx.AsyncClient, uow: SqlUnitOfWork, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource())
    await store_briefs(uow, 1, 2, 3)

    first = (await client.get("/briefs", params={"limit": 2})).json()
    second = (
        await client.get("/briefs", params={"limit": 2, "before": first["next_before"]})
    ).json()

    assert first["next_before"] == "2020-01-02"
    assert [item["date"] for item in second["items"]] == ["2020-01-01"]
    assert second["next_before"] is None


async def test_history_is_empty_when_nothing_is_stored(
    client: httpx.AsyncClient, use_fakes: UseFakes
) -> None:
    use_fakes(FakeSource())

    response = await client.get("/briefs")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == []
