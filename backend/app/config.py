from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app runs with zero setup.
    # Set DATABASE_URL to a postgres:// DSN for production (PostgreSQL is preferred per spec).
    database_url: str = "sqlite:///./ethara.db"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
