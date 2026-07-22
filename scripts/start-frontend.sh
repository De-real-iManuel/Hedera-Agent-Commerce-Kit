#!/usr/bin/env bash
set -euo pipefail

if [ ! -d "frontend/node_modules" ]; then
  echo "ERROR: node_modules not found. Run ./scripts/install.sh first."
  exit 1
fi

# Load .env for NEXT_PUBLIC_API_URL
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "==> Starting frontend on http://localhost:3000"
cd frontend && npm run dev
