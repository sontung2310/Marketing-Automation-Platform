"""Application settings. The only module that reads environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    mongodb_uri: SecretStr | None = None
    mongodb_database: str = "marketing_automation"

    openai_api_key: SecretStr | None = None
    openai_model_agent: str | None = None
    openai_model_router: str | None = None
    openai_model_judge: str | None = None

    mcp_url: str = "http://localhost:8001/mcp"
    default_company_id: str = "cmp_marketing_eye"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
