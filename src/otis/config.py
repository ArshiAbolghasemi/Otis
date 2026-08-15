"""Application configuration loaded from the environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    #: The account SMTP logs in as - a full address, never a display name.
    username: str = ""
    #: A Google *app password*, not the account password.
    password: str = ""
    #: The From header; may carry a display name, e.g. "AI Farm <a@b.com>".
    sender: str = ""
    result_subject: str = "Your AI Farm result is ready"
    #: ``{download_link}`` and ``{expires_in}`` are filled in per result; a body
    #: without ``{download_link}`` gets the link appended instead.
    result_body: str = (
        "Hello, your result for AI Farm is ready.\n"
        "You can download it here (the link expires in {expires_in}):\n"
        "{download_link}\n"
        "Regards, AI Farm"
    )
    error_subject: str = "Your AI Farm request failed"
    error_body: str = (
        "Hello, unfortunately an error occurred while processing your AI Farm request. "
        "Our team has been notified. Details: "
    )

    @field_validator("result_body", "error_body")
    @classmethod
    def _unescape_newlines(cls, value: str) -> str:
        """Allow multi-line bodies to be written on one ``.env`` line."""
        return value.replace("\\n", "\n")

    @field_validator("password")
    @classmethod
    def _strip_spaces(cls, value: str) -> str:
        """Google shows app passwords in groups of four; the spaces are display only."""
        return "".join(value.split())


class MinioSettings(BaseSettings):
    """S3-compatible object storage holding the result archives.

    Defaults suit Cloudflare R2; any MinIO-style endpoint works the same way.
    """

    model_config = SettingsConfigDict(env_prefix="MINIO_", env_file=".env", extra="ignore")

    endpoint_url: str = ""
    bucket: str = "otis"
    access_key: str = ""
    secret_key: str = ""
    region: str = "auto"
    #: Lifetime of the download link. Seven days is the S3 signature maximum.
    link_expiry_seconds: int = 604800


class AIFarmSettings(BaseSettings):
    """Where AI Farm lives.

    ``root`` is the AI Farm working directory: it holds the script
    (``script_name``) and is where the script expects ``from_user/data`` and
    writes ``to_user``.
    """

    model_config = SettingsConfigDict(env_prefix="AIFARM_", env_file=".env", extra="ignore")

    root: Path = Path("/media/ai/ssd/ahmadkalhor")
    script_name: str = "aifarm.py"
    info_csv_template: str = (
        'Product id:,{product_id}\nWhat size do you demand for the model?,"""{model_size}"""'
    )

    @field_validator("info_csv_template")
    @classmethod
    def _unescape_newlines(cls, value: str) -> str:
        """Allow the multi-row template to be written on one ``.env`` line."""
        return value.replace("\\n", "\n")

    @property
    def script_path(self) -> Path:
        return self.root / self.script_name

    @property
    def from_user_dir(self) -> Path:
        return self.root / "from_user"

    @property
    def data_dir(self) -> Path:
        """``path_from_user`` in the AI Farm script."""
        return self.from_user_dir / "data"

    @property
    def info_csv_path(self) -> Path:
        return self.data_dir / "info.csv"

    @property
    def to_user_dir(self) -> Path:
        """``path_to_user`` in the AI Farm script."""
        return self.root / "to_user"


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "otis"
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    mail: MailSettings = Field(default_factory=MailSettings)
    aifarm: AIFarmSettings = Field(default_factory=AIFarmSettings)
    minio: MinioSettings = Field(default_factory=MinioSettings)


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
