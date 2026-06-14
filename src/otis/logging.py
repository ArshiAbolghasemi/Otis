"""Centralised logging configuration for the API and the Celery worker."""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging once for the whole process."""
    global _configured
    if _configured:
        return
    logging.basicConfig(level=level, format=_LOG_FORMAT)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger, ensuring logging is configured first."""
    configure_logging()
    return logging.getLogger(name)
