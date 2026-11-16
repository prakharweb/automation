"""
Space Consultant - Meta Ads + DoubleTick Lead Automation Platform
Configuration Module (app/config.py)
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Space Consultant Lead Automation Platform"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-64-char-random-hex")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    API_PREFIX: str = "/api"

    # Admin Seed Credentials (loaded from environment; never hardcoded in production)
    INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "admin@spaceconsultant.in")
    INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "SpaceAdmin@2026!")
    INITIAL_ADMIN_NAME: str = os.getenv("INITIAL_ADMIN_NAME", "Space Consultant Admin")

    # Database (Neon PostgreSQL in production, SQLite fallback for local/test)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./space_consultant.db",
    )
    DB_SSL_REQUIRE: bool = os.getenv("DB_SSL_REQUIRE", "true").lower() == "true"

    # CORS
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,https://space-consultant-automation.netlify.app",
    )

    # Meta Marketing & Graph API Configuration
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    META_GRAPH_API_VERSION: str = os.getenv("META_GRAPH_API_VERSION", "v21.0")
    META_GRAPH_BASE_URL: str = os.getenv("META_GRAPH_BASE_URL", "https://graph.facebook.com")

    # DoubleTick WhatsApp Business API Configuration
    DOUBLETICK_API_KEY: str = os.getenv("DOUBLETICK_API_KEY", "")
    DOUBLETICK_SENDER: str = os.getenv("DOUBLETICK_SENDER", "")
    DOUBLETICK_WEBHOOK_SECRET: str = os.getenv("DOUBLETICK_WEBHOOK_SECRET", "")
    DOUBLETICK_BASE_URL: str = os.getenv("DOUBLETICK_BASE_URL", "https://public.doubletick.io")

    # Optional Gemini AI Reply Integration
    AI_REPLY_ENABLED: bool = os.getenv("AI_REPLY_ENABLED", "false").lower() == "true"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Optional Google Sheets Webhook/Sync Integration
    GOOGLE_SHEETS_ENABLED: bool = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
    GOOGLE_SHEETS_WEBHOOK_URL: str = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")

    # Follow-up Worker & Rate Limiting
    FOLLOWUP_WORKER_ENABLED: bool = os.getenv("FOLLOWUP_WORKER_ENABLED", "true").lower() == "true"
    FOLLOWUP_POLL_INTERVAL_SECONDS: int = int(os.getenv("FOLLOWUP_POLL_INTERVAL_SECONDS", "60"))
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
    WHATSAPP_REQUIRE_EXPLICIT_CONSENT: bool = os.getenv(
        "WHATSAPP_REQUIRE_EXPLICIT_CONSENT", "false"
    ).lower() == "true"

    @property
    def normalized_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://") and self.DB_SSL_REQUIRE and "sslmode=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return url

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
