#!/usr/bin/env bash
# Apply all pending database migrations.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[otis] Applying database migrations..."
alembic upgrade head
echo "[otis] Migrations applied."
