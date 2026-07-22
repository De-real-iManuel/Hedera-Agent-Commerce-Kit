#!/usr/bin/env bash
set -euo pipefail

VENV="backend/.venv"

if [ ! -d "$VENV" ]; then
  echo "ERROR: venv not found. Run ./scripts/install.sh first."
  exit 1
fi

source "$VENV/bin/activate"

# Load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "==> Starting backend on http://localhost:${BACKEND_PORT:-8000}"
uvicorn backend.main:app \
  --host "${BACKEND_HOST:-0.0.0.0}" \
  --port "${BACKEND_PORT:-8000}" \
  --reload
