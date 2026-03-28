from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────
    app_name: str = "MedTrack ERP"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────
    database_url: str
    database_sync_url: str = ""  # Used only by Alembic

    # ── JWT ──────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    jwt_refresh_expiry_days: int = 7

    # ── CORS ─────────────────────────────────────
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── File Storage ─────────────────────────────
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # ── Redis ────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Email (stub) ──────────────────────────────
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def database_sync_url_computed(self) -> str:
        """Return explicit sync URL or derive from async URL."""
        if self.database_sync_url:
            return self.database_sync_url
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
