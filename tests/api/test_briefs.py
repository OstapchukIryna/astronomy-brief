import datetime as dt
from collections.abc import Callable
from dataclasses import replace

import httpx
import pytest
from fastapi import FastAPI, status

from app.api.dependencies import get_apod_source, get_llm, get_unit_of_work
from app.domain.apod import (
    ApodBadResponseError,
    ApodNotFoundError,
    ApodSource,
    ApodUnavailableError,
)
from app.domain.llm import LlmBadResponseError, LlmClient, LlmUnavailableError
from app.repositories.unit_of_work import SqlUnitOfWork
from tests.fakes import ENTRY, FACTS, FakeLlm, FakeSource


@pytest.fixture
def use_source(app: FastAPI, uow: SqlUnitOfWork) -> Callable[[ApodSource], None]:
    """Make the app use the test session and the given APOD source."""
    app.dependency_overrides[get_unit_of_work] = lambda: uow

    def _use(source: ApodSource) -> None:
        app.dependency_overrides[get_apod_source] = lambda: source
        app.dependency_overrides[get_llm] = lambda: FakeLlm()

    return _use


@pytest.fixture
def use_llm(
    app: FastAPI, use_source: Callable[[ApodSource], None]
) -> Callable[[LlmClient], None]:
    """Make the app use the given LLM."""

    def _use(llm: LlmClient) -> None:
        app.dependency_overrides[get_llm] = lambda: llm

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
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(FakeSource(ENTRY))

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
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(FakeSource(ENTRY))

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
    use_source: Callable[[ApodSource], None],
    error: Exception,
    expected_status: int,
) -> None:
    use_source(FakeSource(error))

    response = await client.get("/briefs/2020-01-01")

    assert response.status_code == expected_status


async def test_does_not_expose_internal_error_details(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(
        FakeSource(
            ApodUnavailableError(
                "Archive returned 503: https://apod.nasa.gov/apod/ap200101.html"
            )
        )
    )

    response = await client.get("/briefs/2020-01-01")

    assert "apod.nasa.gov" not in response.text


async def test_rejects_future_date(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    source = FakeSource(ENTRY)
    use_source(source)

    response = await client.get("/briefs/2100-01-01")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_returns_explanation_for_date(
    client: httpx.AsyncClient,
    use_source: Callable[[ApodSource], None],
    use_llm: Callable[[LlmClient], None],
) -> None:
    use_source(FakeSource())
    use_llm(FakeLlm(explanation="A star is fading."))

    response = await client.get("/briefs/2020-01-01/explanation")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"date": "2020-01-01", "explanation": "A star is fading."}


async def test_returns_facts_for_date(
    client: httpx.AsyncClient,
    use_source: Callable[[ApodSource], None],
    use_llm: Callable[[LlmClient], None],
) -> None:
    use_source(FakeSource())
    use_llm(FakeLlm())

    response = await client.get("/briefs/2020-01-01/facts")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"date": "2020-01-01", "facts": FACTS}


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(LlmUnavailableError("LLM request failed"), 503, id="unavailable"),
        pytest.param(LlmBadResponseError("empty answer"), 502, id="bad-response"),
    ],
)
async def test_maps_llm_errors_to_status(
    client: httpx.AsyncClient,
    use_source: Callable[[ApodSource], None],
    use_llm: Callable[[LlmClient], None],
    error: Exception,
    expected_status: int,
) -> None:
    use_source(FakeSource())
    use_llm(FakeLlm(explanation=error, facts=error))

    response = await client.get("/briefs/2020-01-01/explanation")

    assert response.status_code == expected_status


# history


async def test_history_returns_stored_briefs_newest_first(
    client: httpx.AsyncClient,
    uow: SqlUnitOfWork,
    use_source: Callable[[ApodSource], None],
) -> None:
    use_source(FakeSource())
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
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(FakeSource())

    response = await client.get(
        "/briefs", params={"date_from": "2020-01-02", "date_to": "2020-01-01"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_history_pages_through_all_briefs_by_date(
    client: httpx.AsyncClient,
    uow: SqlUnitOfWork,
    use_source: Callable[[ApodSource], None],
) -> None:
    use_source(FakeSource())
    await store_briefs(uow, 1, 2, 3)

    first = (await client.get("/briefs", params={"limit": 2})).json()
    second = (
        await client.get("/briefs", params={"limit": 2, "before": first["next_before"]})
    ).json()

    assert first["next_before"] == "2020-01-02"
    assert [item["date"] for item in second["items"]] == ["2020-01-01"]
    assert second["next_before"] is None


async def test_history_is_empty_when_nothing_is_stored(
    client: httpx.AsyncClient, use_source: Callable[[ApodSource], None]
) -> None:
    use_source(FakeSource())

    response = await client.get("/briefs")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == []
