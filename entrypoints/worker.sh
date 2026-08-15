#!/usr/bin/env bash
# Start the Celery worker that processes submissions.
set -euo pipefail
cd "$(dirname "$0")/.."

# AI Farm runs one submission at a time (the job also takes a Redis lock, which
# is what keeps additional worker processes in line).
echo "[otis] Starting Celery worker..."
exec celery -A infrastructure.celery.app worker --loglevel=info --concurrency=1
