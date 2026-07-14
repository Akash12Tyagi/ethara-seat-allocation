from functools import lru_cache
from pydantic import field_validator
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
    # Temporary, optional: enables POST /admin/seed for one-time remote seeding
    # on managed platforms where a shell/job primitive isn't available on the
    # free tier. Unset in production once seeding is done - see docs/DEPLOYMENT.md.
    admin_seed_token: str | None = None

    @field_validator("database_url")
    @classmethod
    def _normalize_postgres_scheme(cls, v: str) -> str:
        # Managed Postgres providers (Railway, Heroku, etc.) hand out bare
        # postgres(ql):// URLs, but SQLAlchemy needs the psycopg3 dialect
        # prefix to pick the right driver - rewrite rather than requiring
        # every deploy target to hand-edit the DSN scheme.
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
