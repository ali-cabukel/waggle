"""Application settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    waggle_api_key: str = Field(default="waggle-dev-key")
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="waggle")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"]
    )
    playwright_headless: bool = Field(default=True)
    obscura_bin: str = Field(default="obscura")
    obscura_cdp_url: str = Field(
        default="http://127.0.0.1:9222",
        description="Obscura CDP endpoint from Docker (ws:// or http://). Empty = use local binary.",
    )
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=True)
    max_repair_attempts: int = Field(default=3)
    job_backend: str = Field(
        default="asyncio",
        description="Run queue: asyncio (in-process) or celery (Redis worker)",
    )
    redis_url: str = Field(default="redis://localhost:6380/0")


settings = Settings()
