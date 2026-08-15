"""FastAPI application factory."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from data.router import router as data_router
from model.router import router as model_router
from otis.config import get_settings
from otis.logging import configure_logging, get_logger
from ui.router import register_ui

logger = get_logger(__name__)

#: Everything but the UI is versioned, so the API can change without moving the form.
API_PREFIX = "/v1"


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="AI Farm dataset intake, processing and delivery.",
        version="0.1.0",
    )

    api = APIRouter(prefix=API_PREFIX)

    @api.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    api.include_router(data_router)
    api.include_router(model_router)
    app.include_router(api)

    register_ui(app)
    logger.info("Otis application initialised")
    return app


app = create_app()
