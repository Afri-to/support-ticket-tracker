"""Settings read from environment variables (or a local .env file)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tickets"
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB is plenty for ~50k tickets
    # Send the session cookie only over HTTPS. Turn off for local http://localhost.
    secure_cookies: bool = True
    # Create and fill the read-only demo account at startup.
    seed_demo: bool = True
    # Folder with the built React app (frontend/dist) to serve at "/", if any.
    frontend_dist: str | None = None

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Accept postgres:// and postgresql:// URLs as hosts hand them out."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
