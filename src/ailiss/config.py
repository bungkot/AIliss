from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Lead Intelligence"
    environment: str = "rnd"
    database_url: str = "sqlite:///./data/ailiss.db"
    ollama_base_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen3:0.6b"
    agent_max_steps: int = 8
    agent_max_tool_calls: int = 6
    agent_max_tokens: int = 4000
    agent_max_wall_seconds: float = 30.0
    agent_max_bytes: int = 100_000
    agent_max_spend_usd: float = 0.25

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def database_path(database_url: str) -> Path | None:
    prefix = "sqlite:///./"
    if database_url.startswith(prefix):
        return Path(database_url.removeprefix(prefix))
    if database_url.startswith("sqlite:///"):
        return Path(database_url.removeprefix("sqlite:///"))
    return None
