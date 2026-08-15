"""The upload form: a static page that talks to the upload API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"

router = APIRouter(tags=["ui"])


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the upload form."""
    return FileResponse(STATIC_DIR / "index.html")


def register_ui(app: FastAPI) -> None:
    """Attach the form and the assets it loads to ``app``."""
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
