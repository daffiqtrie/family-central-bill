"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "FamilyCentralAPI"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database (SQLite for local development)
    DATABASE_URL: str = "sqlite+aiosqlite:///./family.db"

    # Security
    FAMILY_API_KEY: str | None = Field(
        default=None,
        description="Static API key expected in the X-FAMILY-KEY request header.",
    )
    EXPOSE_API_DOCS: bool = False

    # CORS (for future use)
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ─────────────────────────────────────────────────────────────────────────
    # Bill Checker URLs (PPOB/Scraping endpoints)
    # ─────────────────────────────────────────────────────────────────────────

    # PLN Postpaid Bill Check
    # Options: PPOB API, PLN Mobile API, Sepulsa, or "mock" for simulation mode
    PLN_CHECK_URL: str = ""
    PLN_API_KEY: str = ""  # API key if required by the endpoint

    # PDAM Bill Check (Padang)
    PDAM_CHECK_URL: str = ""
    PDAM_API_KEY: str = ""

    # Indihome Bill Check
    INDIHOME_CHECK_URL: str = ""
    INDIHOME_API_KEY: str = ""

    # Shared Sepulsa key used by the current provider integrations.
    SEPULSA_API_KEY: str = ""

    # HTTP Client Settings
    HTTP_TIMEOUT: float = 30.0  # Request timeout in seconds
    HTTP_MAX_RETRIES: int = 3  # Max retry attempts

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        """Accept either a JSON-style list or a comma-separated origins string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def docs_enabled(self) -> bool:
        """Return whether interactive API documentation should be exposed."""
        return self.DEBUG or self.EXPOSE_API_DOCS

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def pln_enabled(self) -> bool:
        """Check if real PLN checking is enabled."""
        return bool(self.PLN_CHECK_URL)

    @property
    def pdam_enabled(self) -> bool:
        """Check if real PDAM checking is enabled."""
        return bool(self.PDAM_CHECK_URL)

    @property
    def indihome_enabled(self) -> bool:
        """Check if real Indihome checking is enabled."""
        return bool(self.INDIHOME_CHECK_URL)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
