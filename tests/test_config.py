import pytest
from pydantic import ValidationError

from app.config import Settings

DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/db"


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            llm_model="test-model",
            llm_provider="openai",
            openai_api_key=None,
        )


def test_ollama_provider_works_without_api_key() -> None:
    settings = Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        llm_model="test-model",
        llm_provider="ollama",
        openai_api_key=None,
    )

    assert settings.openai_api_key is None


def test_answer_max_tokens_defaults_to_300(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_ANSWER_MAX_TOKENS", raising=False)
    settings = Settings(
        _env_file=None, database_url=DATABASE_URL, llm_model="test-model"
    )

    assert settings.llm_answer_max_tokens == 300


def test_reads_answer_max_tokens_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_ANSWER_MAX_TOKENS", "123")

    settings = Settings(
        _env_file=None, database_url=DATABASE_URL, llm_model="test-model"
    )

    assert settings.llm_answer_max_tokens == 123


def test_accepts_answer_max_tokens_of_1() -> None:
    settings = Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        llm_model="test-model",
        llm_answer_max_tokens=1,
    )

    assert settings.llm_answer_max_tokens == 1


@pytest.mark.parametrize(
    "value", [pytest.param(0, id="zero"), pytest.param(-1, id="negative")]
)
def test_rejects_answer_max_tokens_below_1(value: int) -> None:
    with pytest.raises(ValidationError, match="llm_answer_max_tokens"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            llm_model="test-model",
            llm_answer_max_tokens=value,
        )
