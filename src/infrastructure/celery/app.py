"""Celery application instance."""

from __future__ import annotations

from celery import Celery

from otis.config import get_settings
from otis.logging import configure_logging

configure_logging()

_settings = get_settings()

celery_app = Celery(
    "otis",
    broker=_settings.celery.broker_url,
    backend=_settings.celery.result_backend,
    include=["aifarm.job"],
)

celery_app.conf.update(
    task_track_started=True,
    # AI Farm works out of fixed directories, so submissions are processed one
    # at a time: a single slot per worker, and no queue hoarding so a busy
    # worker's backlog stays available to the others.
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
