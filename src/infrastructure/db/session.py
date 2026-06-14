"""SQLAlchemy engine and session factory (synchronous)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from otis.config import get_settings

_settings = get_settings()

engine = create_engine(_settings.database.url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager yielding a session, for use outside FastAPI (e.g. Celery)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
