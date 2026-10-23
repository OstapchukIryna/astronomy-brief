import json
from typing import Literal

import pytest
import respx
from pydantic import SecretStr

from app.bootstrap import build_container
from app.config import Settings
from app.domain.questions import Question
from tests.fakes import ENTRY

OPENAI_BASE_URL = "https://api.openai.com/v1"


async def test_openai_provider_calls_openai_with_api_key(
    respx_mock: respx.MockRouter,
) -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+psycopg://unused/db"),
        llm_provider="openai",
        llm_model="gpt-test",
        openai_api_key=SecretStr("sk-test"),
    )
    route = respx_mock.post(f"{OPENAI_BASE_URL}/chat/completions").respond(
        200, json={"choices": [{"message": {"content": "A star is fading."}}]}
    )

    async with build_container(settings) as container:
        await container.llm.explain(ENTRY)

    assert route.calls.last.request.headers["Authorization"] == "Bearer sk-test"


@pytest.mark.parametrize(
    ("provider", "completions_url"),
    [
        pytest.param(
            "ollama", "http://localhost:11434/v1/chat/completions", id="ollama"
        ),
        pytest.param("openai", f"{OPENAI_BASE_URL}/chat/completions", id="openai"),
    ],
)
async def test_llm_client_gets_the_answer_token_limit(
    respx_mock: respx.MockRouter,
    provider: Literal["ollama", "openai"],
    completions_url: str,
) -> None:
    settings = Settings(
        _env_file=None,
        database_url=SecretStr("postgresql+psycopg://unused/db"),
        llm_provider=provider,
        llm_model="test-model",
        openai_api_key=SecretStr("sk-test"),
        llm_answer_max_tokens=123,
    )
    route = respx_mock.post(completions_url).respond(
        200, json={"choices": [{"message": {"content": "It is losing brightness."}}]}
    )

    async with build_container(settings) as container:
        await container.llm.answer(ENTRY, Question("Why is Betelgeuse fading?"))

    assert json.loads(route.calls.last.request.content)["max_tokens"] == 123
