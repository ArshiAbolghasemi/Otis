"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from otis.config import get_settings
from otis.logging import configure_logging, get_logger
from webhook.router import router as webhook_router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Webhook-driven AI Farm processing service.",
        version="0.1.0",
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(webhook_router)
    logger.info("Otis application initialised")
    return app


app = create_app()
