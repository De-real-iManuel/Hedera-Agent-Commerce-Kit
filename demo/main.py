"""
demo/main.py
-------------
FastAPI application entry point for the HACK demo.

Responsibilities (wiring only — no business logic):
  1. Create ONE ServiceContainer at startup.
  2. Attach it to app.state.container for use by all routers.
  3. Register X402Middleware with the lifecycle service.
  4. Register all routers.

All payment logic, state management, and compliance rules live in the hack/
toolkit package.  This file intentionally contains nothing but wiring.

Quick reference:
  GET  /api/health
  POST /api/payment/challenge
  POST /api/payment/verify
  GET  /api/payment/status/{quote_id}
  GET  /api/premium-query          ← x402 gated
  GET  /api/receipt/{tx_id}
  GET  /api/usage
  GET  /api/hashscan/{tx_id}
  GET  /api/agent/query
  POST /api/agent/query
  POST /api/compliance/check
  GET  /api/compliance/certify/{quote_id}

Interactive docs: http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hack.container import ServiceContainer
from hack.middleware.x402 import X402Middleware

from demo.routers import (
    agent,
    compliance,
    hashscan,
    health,
    payment,
    premium,
    receipts,
    usage,
)

# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Hedera Agent Commerce Kit",
    description=(
        "**Pay-per-request infrastructure for AI agents, APIs, and MCP tools — "
        "powered by Hedera x402, HBAR, Mirror Node, and HCS.**\n\n"
        "## How it works\n"
        "1. Call a protected endpoint → receive HTTP 402 with a payment challenge\n"
        "2. Send HBAR to the receiver account\n"
        "3. POST your transaction ID to `/api/payment/verify`\n"
        "4. Retry the endpoint with `X-Payment-Token` and `X-Quote-Id` headers\n"
        "5. Receive the response + an immutable HCS receipt\n\n"
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
        "url": "https://github.com/your-org/hedera-agent-commerce-kit",
    },
    license_info={"name": "MIT"},
)

# ─── Service container (one per process) ─────────────────────────────────────

@app.on_event("startup")
async def _startup() -> None:
    container = ServiceContainer.from_settings()
    app.state.container = container


# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── x402 payment gate ───────────────────────────────────────────────────────
# The lifecycle service is retrieved at middleware construction time from the
# container.  Since the middleware is added before startup completes, we build
# a temporary container here solely for the middleware; the startup handler
# replaces app.state.container with the canonical one.
#
# To avoid building the container twice, we create it once here and also
# assign it to app.state directly.

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
