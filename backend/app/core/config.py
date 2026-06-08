from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://opensteps:opensteps@postgres:5432/opensteps"
    service_private_key: str | None = None
    cors_origins: list[str] = Field(default=["http://localhost:3000"])
    approval_ttl_seconds: int = 3600
    http_allowlisted_domains: list[str] = Field(default=["httpbin.org"])


@lru_cache
def get_settings() -> Settings:
    return Settings()

