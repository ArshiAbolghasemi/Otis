# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install uv for fast, reproducible dependency installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies first to leverage layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv pip install --system .

# Application entrypoints and migrations.
COPY main.py alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
RUN chmod +x scripts/*.sh

EXPOSE 8000
