#!/usr/bin/env bash
# Apply migrations, then start the Otis API server.
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/migrate.sh

HOST="${OTIS_HOST:-0.0.0.0}"
PORT="${OTIS_PORT:-8000}"
echo "[otis] Starting API on ${HOST}:${PORT}..."
exec uvicorn otis.app:app --host "${HOST}" --port "${PORT}"
