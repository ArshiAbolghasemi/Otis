"""Application configuration loaded from the environment / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "otis"
    password: str = "otis"
    db: str = "otis"

    @property
    def url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
        )


class CelerySettings(BaseSettings):
    """Celery broker / result backend settings (Redis)."""

    model_config = SettingsConfigDict(env_prefix="CELERY_", env_file=".env", extra="ignore")

    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"


class MailSettings(BaseSettings):
    """Gmail SMTP settings and the templated messages."""

    model_config = SettingsConfigDict(env_prefix="GMAIL_", env_file=".env", extra="ignore")

    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    result_subject: str = "Your AI Farm result is ready"
    result_body: str = (
        "Hello, your result for AI Farm is ready. "
        "Please find the output attached to this email. Regards, AI Farm"
    )
    error_subject: str = "Your AI Farm request failed"
    error_body: str = (
        "Hello, unfortunately an error occurred while processing your AI Farm request. "
        "Our team has been notified. Details: "
    )


class WebhookSettings(BaseSettings):
    """Inbound webhook authentication settings."""

    model_config = SettingsConfigDict(env_prefix="WEBHOOK_", env_file=".env", extra="ignore")

    api_key: str = Field(default="")


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "otis"
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    mail: MailSettings = Field(default_factory=MailSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
