# Backend Dockerfile for Hedera Agent Commerce Kit (HACK)
# Runs the FastAPI app at demo.main:app.
#
# Build:
#   docker build -t hack-backend .
# Run:
#   docker run --env-file .env -p 8000:8000 -v hack_data:/app/data -v hack_state:/app/state hack-backend

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    COMPLIANCE_STORE_DIR=/app/data/reports \
    HACK_STATE_FILE=/app/state/.hack_state.json

WORKDIR /app

# Minimal system deps. curl is used for the container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY hack ./hack
COPY demo ./demo

# Install core backend plus Hedera SDK extra for real HCS/NFT operations.
RUN pip install --upgrade pip \
    && pip install -e ".[hedera]"

# Runtime writable locations. Mount /app/data and /app/state in production.
RUN mkdir -p /app/data/reports /app/state

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/api/health || exit 1

CMD ["sh", "-c", "uvicorn demo.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
