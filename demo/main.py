"""
demo/main.py
-------------
FastAPI application entry point for the HACK demo.

Wiring only — no business logic. All payment/audit/compliance logic lives in
the `hack/` toolkit package.

Interactive docs: http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hack.container import ServiceContainer
from hack.middleware.x402 import X402Middleware

from demo.routers import (
    agent,
    audit,
    compliance,
    hashscan,
    health,
    payment,
    premium,
    receipts,
    usage,
)


def _cors_origins() -> list[str]:
    """Return explicit production frontend origins from env.

    Set either:
    - FRONTEND_ORIGIN=https://your-frontend.example.com
    - CORS_ALLOW_ORIGINS=https://a.example.com,https://b.example.com
    """
    raw = os.getenv("CORS_ALLOW_ORIGINS") or os.getenv("FRONTEND_ORIGIN") or ""
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Hedera Agent Commerce Kit",
    description=(
        "**Pay-per-request infrastructure for AI agents, APIs, and MCP tools — "
        "powered by Hedera x402, HBAR, Mirror Node, and HCS.**\n\n"
        "## Endpoints\n"
        "* Payment flow — `/api/payment/*`, `/api/premium-query`\n"
        "* Compliance (per-tx) — `/api/compliance/*`\n"
        "* Service audits + soulbound NFTs — `/api/audit/*`\n\n"
        "## Developer shortcut\n"
        "```python\n"
        "from hack import PaidEndpoint\n\n"
        "@app.get('/my-endpoint')\n"
        "@PaidEndpoint(price='0.5 HBAR')\n"
        "async def my_endpoint(request: Request):\n"
        "    return {'result': 'paid access granted'}\n"
        "```"
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Hedera Agent Commerce Kit",
        "url": "https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit",
    },
    license_info={"name": "MIT"},
)


# ─── Service container (one per process) ─────────────────────────────────────

@app.on_event("startup")
async def _startup() -> None:
    # The bootstrap container built below is already assigned to app.state;
    # re-assign here for clarity and to trigger any lazy singletons that
    # depend on startup timing.
    app.state.container = _bootstrap_container


# ─── CORS ────────────────────────────────────────────────────────────────────
# Localhost regex covers every dev port. Production origins are supplied via
# FRONTEND_ORIGIN or CORS_ALLOW_ORIGINS.

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?"      # local dev
        r"|https://[a-zA-Z0-9-]+\.vercel\.app"            # Vercel
        r"|https://[a-zA-Z0-9-]+\.ngrok-free\.app"        # ngrok
        r"|https://[a-zA-Z0-9-]+\.up\.railway\.app"       # Railway
        r"|https://[a-zA-Z0-9-]+\.onrender\.com"          # Render
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── x402 payment gate ───────────────────────────────────────────────────────
# Middleware needs the lifecycle instance at construction time, so we build the
# container BEFORE routers/middleware are registered, and reuse it in startup.

_bootstrap_container = ServiceContainer.from_settings()
app.state.container = _bootstrap_container

app.add_middleware(
    X402Middleware,
    lifecycle=_bootstrap_container.lifecycle,
    protected_routes={"/api/premium-query"},
)


# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(health.router, prefix="/api")
app.include_router(payment.router, prefix="/api")
app.include_router(receipts.router, prefix="/api")
app.include_router(usage.router, prefix="/api")
app.include_router(premium.router, prefix="/api")
app.include_router(hashscan.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
