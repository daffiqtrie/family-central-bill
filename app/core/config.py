"""Application configuration using pydantic-settings."""

from functools import lru_cache

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
    DEBUG: bool = True  # Default to True for local development
    API_V1_PREFIX: str = "/api/v1"

    # Database (SQLite for local development)
    DATABASE_URL: str = "sqlite+aiosqlite:///./family.db"

    # Security
    FAMILY_API_KEY: str = "change-this-in-production"

    # CORS (for future use)
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # ─────────────────────────────────────────────────────────────────────────
    # Bill Checker URLs (PPOB/Scraping endpoints)
    # ─────────────────────────────────────────────────────────────────────────
    
    # PLN Postpaid Bill Check
    # Options: PPOB API, PLN Mobile API, or web scraping endpoint
    # Set to empty string to use mock/simulation mode
    PLN_CHECK_URL: str = ""
    PLN_API_KEY: str = ""  # API key if required by the endpoint
    
    # PDAM Bill Check (Padang)
    PDAM_CHECK_URL: str = ""
    PDAM_API_KEY: str = ""
    
    # Indihome Bill Check
    INDIHOME_CHECK_URL: str = ""
    INDIHOME_API_KEY: str = ""
    
    # HTTP Client Settings
    HTTP_TIMEOUT: float = 30.0  # Request timeout in seconds
    HTTP_MAX_RETRIES: int = 3   # Max retry attempts

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
