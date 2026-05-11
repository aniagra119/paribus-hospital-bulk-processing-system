"""
Application configuration via environment variables.

Uses Pydantic Settings to load values from .env file or system environment.
All configurable values are centralized here to avoid magic strings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
    )

    PROJECT_NAME: str = "Hospital Bulk Processing System"
    API_V1_STR: str = "/api/v1"
    UPSTREAM_API_URL: str = "https://hospital-directory.onrender.com"


settings = Settings()
