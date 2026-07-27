# ─── Builder stage ────────────────────────────────────────────────────────────
# Compiles/downloads all Python wheels so the runtime image never needs
# build tools or a package cache.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install wheels into a prefix we can copy wholesale into the runtime image.
COPY pyproject.toml README.md ./
COPY hack ./hack

RUN pip install --upgrade pip \
    && pip install --prefix=/install -e ".[hedera]"

# ─── Runtime stage ────────────────────────────────────────────────────────────
# Lean image — no compiler, no pip cache, no build-time artefacts.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    COMPLIANCE_STORE_DIR=/app/data/reports \
    HACK_STATE_FILE=/app/state/.hack_state.json

WORKDIR /app

# curl for the HEALTHCHECK only — nothing else needed at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder.
COPY --from=builder /install /usr/local

# Copy only application source — no pyproject.toml, no test dirs, no scripts.
COPY hack ./hack
COPY demo ./demo

# Writable data/state dirs; mount volumes in production.
RUN mkdir -p /app/data/reports /app/state

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT:-8000}/api/health || exit 1

# Render sets $PORT dynamically (usually 10000). Fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn demo.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
