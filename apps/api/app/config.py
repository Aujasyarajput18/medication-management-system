"""
Aujasya — Application Configuration
Loads all environment variables via Pydantic Settings.
[FIX-17] pydantic-settings is a separate package from pydantic v2.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "Aujasya"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://aujasya:password@localhost:5432/aujasya_dev"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_DB: int = 1
    REDIS_RATE_LIMIT_DB: int = 2

    # ── Security ──────────────────────────────────────────────────────────
    SECRET_KEY: str = "change_me_in_production_64_char_random_hex_string_here_abcdef12"
    ENCRYPTION_MASTER_KEY: str = "change_me_in_production_64_char_random_hex_aes_master_key_here"
    ENCRYPTION_KEY_VERSION: str = "v1"

    # ── Authentication ────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    # ── SMS (Msg91) ───────────────────────────────────────────────────────
    MSG91_API_KEY: str = ""
    MSG91_SENDER_ID: str = "AUJASY"
    MSG91_TEMPLATE_ID_OTP: str = ""
    MSG91_TEMPLATE_ID_REMINDER: str = ""

    # ── WhatsApp (Wati) ───────────────────────────────────────────────────
    WATI_API_URL: str = "https://live-mt-server.wati.io"
    WATI_API_TOKEN: str = ""
    WATI_TEMPLATE_CAREGIVER_ALERT: str = ""
    WATI_TEMPLATE_REFILL_REMINDER: str = ""
    WATI_TEMPLATE_CAREGIVER_INVITE: str = ""

    # ── Firebase ──────────────────────────────────────────────────────────
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_KEY: str = ""
    FIREBASE_WEB_API_KEY: str = ""

    # ── Celery ────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/3"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/4"

    # ── Sentry ────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        """
        Convert async DB URL to sync URL for Celery tasks.
        [FIX-6] Celery cannot use async SQLAlchemy.
        """
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.APP_ENV == "testing"


settings = Settings()
