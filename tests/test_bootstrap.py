import respx
from pydantic import SecretStr

from app.bootstrap import build_container
from app.config import Settings
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
