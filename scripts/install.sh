#!/usr/bin/env bash
set -euo pipefail

echo "==> Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required. Install Python 3.10+ and re-run."
  exit 1
fi

if ! command -v node &>/dev/null; then
  echo "ERROR: node is required. Install Node.js 18+ and re-run."
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "==> Python $PYTHON_VERSION found."

# ─── Backend ──────────────────────────────────────────────────────────────────
echo "==> Setting up Python virtual environment..."
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt --quiet
deactivate
echo "==> Backend dependencies installed."

# ─── Frontend ─────────────────────────────────────────────────────────────────
echo "==> Installing frontend dependencies..."
cd frontend && npm install --silent && cd ..
echo "==> Frontend dependencies installed."

# ─── .env ─────────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — fill in your Hedera credentials."
fi

echo ""
echo "✅ Installation complete."
echo "   Start backend:  ./scripts/start-backend.sh"
echo "   Start frontend: ./scripts/start-frontend.sh"
