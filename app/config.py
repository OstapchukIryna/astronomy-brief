from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: SecretStr
    test_database_url: SecretStr | None = None

    nasa_api_key: SecretStr = SecretStr("DEMO_KEY")
    http_timeout_seconds: float = 10.0

    llm_provider: Literal["openai", "ollama"] = "ollama"
    llm_model: str
    openai_api_key: SecretStr | None = None
    ollama_base_url: HttpUrl = HttpUrl("http://localhost:11434/v1")
    llm_timeout_seconds: float = 60.0

    @model_validator(mode="after")
    def _require_openai_key(self) -> Self:
        if self.llm_provider == "openai" and self.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
