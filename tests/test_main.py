import httpx
import respx
from pydantic import SecretStr

from app.config import Settings
from app.main import OPENAI_BASE_URL, _build_llm
from tests.fakes import ENTRY


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

    async with httpx.AsyncClient() as http:
        await _build_llm(http, settings).explain(ENTRY)

    assert route.calls.last.request.headers["Authorization"] == "Bearer sk-test"
