"""FastAPI dependencies for the webhook endpoint."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from infrastructure.db.session import get_session
from otis.config import Settings, get_settings
from webhook.service import WebhookService

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def verify_api_key(
    x_api_key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """Reject requests whose ``x-api-key`` header is missing or does not match."""
    if not settings.webhook.api_key or x_api_key != settings.webhook.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def get_webhook_service(session: Session = Depends(get_session)) -> WebhookService:
    return WebhookService(session)
