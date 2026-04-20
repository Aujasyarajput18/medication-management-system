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

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2 — AI Intelligence & Clinical Decision Layer
    # ══════════════════════════════════════════════════════════════════════

    # ── Bhashini (Voice STT/TTS) ──────────────────────────────────────────
    BHASHINI_API_KEY: str = ""
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_URL: str = "https://dhruva-api.bhashini.gov.in"
    BHASHINI_STT_SERVICE_ID: str = ""
    BHASHINI_TTS_SERVICE_ID: str = ""
    BHASHINI_NMT_SERVICE_ID: str = ""

    # ── Ekacare (Medicine Database) ───────────────────────────────────────
    EKACARE_API_URL: str = "https://api.ekacare.com"
    EKACARE_API_KEY: str = ""
    EKACARE_RATE_LIMIT_PER_MINUTE: int = 60

    # ── PMBJP (Jan Aushadhi) ─────────────────────────────────────────────
    PMBJP_API_URL: str = "https://janaushadhi.gov.in/api"
    PMBJP_API_KEY: str = ""
    PMBJP_LOCATOR_RADIUS_KM: int = 25

    # ── Prayer Times APIs ─────────────────────────────────────────────────
    ALADHAN_API_URL: str = "https://api.aladhan.com/v1"
    SUNRISE_SUNSET_API_URL: str = "https://api.sunrise-sunset.org"

    # ── Drug Interaction APIs ─────────────────────────────────────────────
    RXNORM_API_URL: str = "https://rxnav.nlm.nih.gov/REST"
    OPENFDA_API_URL: str = "https://api.fda.gov/drug"
    OPENFDA_API_KEY: str = ""

    # ── Exotel (IVR) ─────────────────────────────────────────────────────
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_CALLER_ID: str = ""

    # ── AI Models ─────────────────────────────────────────────────────────
    PILL_MODEL_VERSION: str = "v1"
    PILL_MODEL_CONFIDENCE_THRESHOLD: float = 0.70
    PILL_MODEL_MOCK: bool = True  # Returns synthetic results when True

    # ── LLaVA Microservice ────────────────────────────────────────────────
    LLAVA_SERVICE_URL: str = "http://llava-service:8001"
    LLAVA_CONFIDENCE_THRESHOLD: float = 0.65
    LLAVA_MAX_IMAGE_SIZE_MB: int = 10
    LLAVA_MOCK: bool = True  # Returns fixture JSON when True

    # ── Redis (Phase 2 cache additions) ───────────────────────────────────
    REDIS_TTS_CACHE_DB: int = 5
    REDIS_PRAYER_CACHE_DB: int = 6

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
