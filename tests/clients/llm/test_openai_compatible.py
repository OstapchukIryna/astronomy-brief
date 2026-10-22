import datetime as dt
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.clients.llm.openai_compatible import OpenAICompatibleLlmClient
from app.domain.apod import ApodEntry, MediaType
from app.domain.facts import Facts
from app.domain.llm import LlmBadResponseError, LlmUnavailableError
from app.domain.questions import Question

BASE_URL = "http://llm.test/v1"
COMPLETIONS_URL = f"{BASE_URL}/chat/completions"
ENTRY = ApodEntry(
    date=dt.date(2020, 1, 1),
    title="Betelgeuse Imagined",
    explanation="Betelgeuse is only half as bright as it used to be.",
    media_type=MediaType.IMAGE,
    url="https://example.com/betelgeuse.jpg",
)
QUESTION = Question("Why is Betelgeuse fading?")
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
        answer_max_tokens=300,
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


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        pytest.param('{"on_topic": true}', True, id="on-topic"),
        pytest.param('{"on_topic": false}', False, id="off-topic"),
        pytest.param(
            '{"on_topic": true, "reason": "about the star"}', True, id="extra-key"
        ),
    ],
)
async def test_is_on_topic_reads_the_classifier_answer(
    llm: OpenAICompatibleLlmClient,
    respx_mock: respx.MockRouter,
    content: str,
    expected: bool,
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, json=completion(content))

    assert await llm.is_on_topic(ENTRY, QUESTION) is expected


async def test_is_on_topic_sends_only_the_title_and_the_question(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion('{"on_topic": true}')
    )

    await llm.is_on_topic(ENTRY, QUESTION)

    body = json.loads(route.calls.last.request.content)
    user_message = body["messages"][-1]["content"]
    assert ENTRY.title in user_message
    assert QUESTION.text in user_message
    assert ENTRY.explanation not in user_message
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["on_topic"]["type"] == "boolean"
    assert body["temperature"] == 0
    assert body["max_tokens"] == 20


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("yes", id="not-json"),
        pytest.param("{}", id="no-key"),
        pytest.param('{"on_topic": null}', id="null"),
        pytest.param('{"on_topic": "true"}', id="string"),
        pytest.param('{"on_topic": 1}', id="number"),
        pytest.param('```json\n{"on_topic": true}\n```', id="fenced"),
    ],
)
async def test_is_on_topic_rejects_answers_that_are_not_a_strict_boolean(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter, content: str
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, json=completion(content))

    with pytest.raises(LlmBadResponseError):
        await llm.is_on_topic(ENTRY, QUESTION)


@pytest.mark.parametrize(
    "ask",
    [
        pytest.param(lambda llm: llm.is_on_topic(ENTRY, QUESTION), id="classifier"),
        pytest.param(lambda llm: llm.answer(ENTRY, QUESTION), id="answer"),
    ],
)
@pytest.mark.parametrize(
    "status",
    [pytest.param(400, id="bad-request"), pytest.param(503, id="server-error")],
)
async def test_question_errors_leave_out_the_provider_message(
    llm: OpenAICompatibleLlmClient,
    respx_mock: respx.MockRouter,
    ask: Callable[[OpenAICompatibleLlmClient], Awaitable[object]],
    status: int,
) -> None:
    route = respx_mock.post(COMPLETIONS_URL).respond(
        status, json={"error": {"message": "Cannot answer: Why is Betelgeuse fading?"}}
    )

    with pytest.raises((LlmBadResponseError, LlmUnavailableError)) as error:
        await ask(llm)

    assert str(error.value) == f"LLM returned {status}"
    assert route.call_count == 1


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        pytest.param("ollama_on_topic.json", True, id="on-topic"),
        pytest.param("ollama_off_topic.json", False, id="off-topic"),
    ],
)
async def test_is_on_topic_reads_recorded_ollama_answers(
    llm: OpenAICompatibleLlmClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
    fixture: str,
    expected: bool,
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, text=read_fixture(fixture))

    assert await llm.is_on_topic(ENTRY, QUESTION) is expected


async def test_answer_returns_the_text_trimmed(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion("  It is losing brightness.\n")
    )

    assert await llm.answer(ENTRY, QUESTION) == "It is losing brightness."


async def test_answer_sends_the_question_with_the_apod_text(
    http: httpx.AsyncClient, respx_mock: respx.MockRouter
) -> None:
    llm = OpenAICompatibleLlmClient(
        http,
        base_url=BASE_URL,
        api_key="test-key",
        model="test-model",
        answer_max_tokens=123,
    )
    route = respx_mock.post(COMPLETIONS_URL).respond(
        200, json=completion("It is losing brightness.")
    )

    await llm.answer(ENTRY, QUESTION)

    body = json.loads(route.calls.last.request.content)
    system_message = body["messages"][0]["content"]
    user_message = body["messages"][-1]["content"]
    assert ENTRY.title in user_message
    assert ENTRY.explanation in user_message
    assert QUESTION.text in user_message
    assert "up to 3 short sentences" in system_message
    assert "English" in system_message
    assert body["max_tokens"] == 123


@pytest.mark.parametrize(
    "content", [pytest.param(None, id="no-content"), pytest.param("  \n", id="blank")]
)
async def test_answer_rejects_an_empty_answer(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter, content: str | None
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(200, json=completion(content))

    with pytest.raises(LlmBadResponseError):
        await llm.answer(ENTRY, QUESTION)


async def test_answer_returns_a_text_cut_by_the_token_limit(
    llm: OpenAICompatibleLlmClient, respx_mock: respx.MockRouter
) -> None:
    truncated = completion("It is losing bright")
    truncated["choices"][0]["finish_reason"] = "length"
    respx_mock.post(COMPLETIONS_URL).respond(200, json=truncated)

    assert await llm.answer(ENTRY, QUESTION) == "It is losing bright"


async def test_answer_reads_a_recorded_ollama_answer(
    llm: OpenAICompatibleLlmClient,
    respx_mock: respx.MockRouter,
    read_fixture: Callable[[str], str],
) -> None:
    respx_mock.post(COMPLETIONS_URL).respond(
        200, text=read_fixture("ollama_answer.json")
    )

    assert await llm.answer(ENTRY, QUESTION) == (
        "Betelgeuse is fading because it is going through a period of dimming, "
        "which is normal for a variable star like Betelgeuse. This dimming can be "
        "caused by changes in its atmosphere or the presence of dust clouds "
        "around the star."
    )
