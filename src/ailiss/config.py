from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Lead Intelligence"
    environment: str = "rnd"
    database_url: str = "sqlite:///./data/ailiss.db"

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
