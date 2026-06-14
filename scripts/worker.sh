#!/usr/bin/env bash
# Start the Celery worker that processes submissions.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[otis] Starting Celery worker..."
exec celery -A infrastructure.celery.app worker --loglevel=info
