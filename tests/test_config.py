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
