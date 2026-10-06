"""Application settings. The only module that reads environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root .env is shared by the backend and dev tooling (e.g. the MongoDB MCP).
# In containers it is absent and the environment is injected instead.
REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"
    log_level: str = "INFO"

    mongodb_uri: SecretStr | None = None
    mongodb_database: str = "marketing_automation"
    competitorscope_database: str = "competitors_monitoring_test"
    dct_database: str = "influencer_discovery"
    pace_database: str = "pace_database"

    openai_api_key: SecretStr | None = None
    openai_model_agent: str = "gpt-5.6-luna"
    openai_model_router: str | None = None

    mcp_url: str = "http://localhost:8001/mcp"
    mcp_allowed_hosts: list[str] = ["localhost:*", "127.0.0.1:*", "[::1]:*", "mcp:8001"]
    default_company_id: str = "cmp_marketing_eye"
    # Agent runs the public demo may start per UTC day (cost guard); 0 disables runs.
    max_runs_per_day: int = Field(default=50, ge=0)
    # Largest vendored skill file is ~24k characters; the cap bounds prompt tokens.
    skill_max_chars: int = 25_000
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
