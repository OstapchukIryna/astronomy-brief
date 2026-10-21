import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.clients.llm.openai_compatible import OpenAICompatibleLlmClient
from app.domain.apod import ApodEntry, MediaType
from app.domain.facts import Facts
from app.domain.llm import LlmBadResponseError, LlmUnavailableError

BASE_URL = "http://llm.test/v1"
COMPLETIONS_URL = f"{BASE_URL}/chat/completions"
ENTRY = ApodEntry(
    date=dt.date(2020, 1, 1),
    title="Betelgeuse Imagined",
    explanation="Betelgeuse is only half as bright as it used to be.",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)
RECORDED_FACTS = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "ollama_facts.json").read_text(
        encoding="utf-8"
    )
)


def completion(content: str | None) -> dict[str, Any]:
    """Changing real recorded Ollama completion."""
    choice = RECORDED_FACTS["choices"][0]
    return {
        **RECORDED_FACTS,
        "choices": [{**choice, "message": {**choice["message"], "content": content}}],
    }


@pytest.fixture
def llm(http: httpx.AsyncClient) -> OpenAICompatibleLlmClient:
    return OpenAICompatibleLlmClient(
        http,
        base_url=BASE_URL,
        api_key="test-key",
        model="test-model",
    )


async def test_explain_returns_text(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion("  A star is fading.  ")
    )

    assert await llm.explain(ENTRY) == "A star is fading."


async def test_explain_grounds_the_model_in_the_apod_text(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion("A star is fading.")
    )

    await llm.explain(ENTRY)

    request = route.calls.last.request
    body = json.loads(request.content)
    assert request.headers["Authorization"] == "Bearer test-key"
    assert body["model"] == "test-model"
    assert ENTRY.explanation in body["messages"][-1]["content"]


async def test_extract_facts_returns_facts(
    llm: OpenAICompatibleLlmClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        200, text=read_fixture("ollama_facts.json")
    )

    assert await llm.extract_facts(ENTRY) == Facts(
        (
            "Betelgeuse is a red supergiant star in the constellation Orion.",
            "Betelgeuse has a diameter about 1,000 times that of the Sun.",
            "Betelgeuse is expected to go supernova at some point in the future.",
            "Betelgeuse has a mass around 20 times that of the Sun.",
        )
    )


async def test_extract_facts_asks_for_json_schema(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    facts = ["It is red.", "It is fading.", "It is far."]
    route = respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion(json.dumps({"facts": facts}))
    )

    await llm.extract_facts(ENTRY)

    body = json.loads(route.calls.last.request.content)
    assert body["response_format"]["type"] == "json_schema"


async def test_extract_facts_cleans_the_answer(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    facts = ["  It is red. ", "", "It is fading.", "it is RED.", "It is far."]
    respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion(json.dumps({"facts": facts}))
    )

    assert await llm.extract_facts(ENTRY) == Facts(
        ("It is red.", "It is fading.", "It is far.")
    )


async def test_extract_facts_keeps_at_most_five(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    facts = ["A.", "B.", "C.", "D.", "E.", "F."]
    respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion(json.dumps({"facts": facts}))
    )

    assert await llm.extract_facts(ENTRY) == Facts(("A.", "B.", "C.", "D.", "E."))


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("not json", id="not-json"),
        pytest.param(json.dumps({"items": ["a", "b", "c"]}), id="wrong-shape"),
        pytest.param(json.dumps({"facts": []}), id="empty-list"),
        pytest.param(json.dumps({"facts": ["One.", "Two."]}), id="two-facts"),
        pytest.param(
            json.dumps({"facts": ["Same.", "same.", "Other."]}),
            id="too-few-after-repeats",
        ),
    ],
)
async def test_extract_facts_rejects_bad_answers(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter, content: str
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, json=completion(content))

    with pytest.raises(LlmBadResponseError):
        await llm.extract_facts(ENTRY)


@pytest.mark.parametrize(
    "content", [pytest.param(None, id="no-content"), pytest.param("   ", id="blank")]
)
async def test_explain_rejects_empty_answer(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter, content: str | None
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, json=completion(content))

    with pytest.raises(LlmBadResponseError):
        await llm.explain(ENTRY)


@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        pytest.param(503, LlmUnavailableError, id="server-error"),
        pytest.param(400, LlmBadResponseError, id="bad-request"),
    ],
)
async def test_maps_error_status(
    llm: OpenAICompatibleLlmClient,
    respx_mock: respx.MockRouter,
    status: int,
    expected_error: type[Exception],
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        status, json={"error": {"message": "nope"}}
    )

    with pytest.raises(expected_error):
        await llm.explain(ENTRY)


async def test_rejects_malformed_completion(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, json={"choices": []})

    with pytest.raises(LlmBadResponseError):
        await llm.explain(ENTRY)


async def test_error_includes_provider_message(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        400, json={"error": {"message": "model is required"}}
    )

    with pytest.raises(LlmBadResponseError, match="400: model is required"):
        await llm.explain(ENTRY)


async def test_error_hides_auth_error_message(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        401, json={"error": {"message": "Incorrect API key provided: sk-abc***xyz"}}
    )

    with pytest.raises(LlmBadResponseError) as error:
        await llm.explain(ENTRY)

    assert str(error.value) == "LLM returned 401"


async def test_error_without_provider_message(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(502, text="<html>Bad Gateway</html>")

    with pytest.raises(LlmUnavailableError) as error:
        await llm.explain(ENTRY)

    assert str(error.value) == "LLM returned 502"


async def test_extract_facts_asks_for_three_to_five_facts(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion(json.dumps({"facts": ["A.", "B.", "C."]}))
    )

    await llm.extract_facts(ENTRY)

    body = json.loads(route.calls.last.request.content)
    assert "Return 3 to 5 facts." in body["messages"][0]["content"]
