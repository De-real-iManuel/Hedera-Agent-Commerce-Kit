"""
Hedera Agent Commerce Kit — Backend
=====================================
FastAPI application entry point.

Quick reference:
  GET  /api/health            — health check
  GET  /api/demo              — free demo endpoint
  POST /api/payment/challenge — issue an HTTP 402 payment challenge
  POST /api/payment/verify    — verify a Hedera HBAR payment
  GET  /api/payment/status/{quote_id}
  GET  /api/premium-query     — example paid endpoint (requires x402 payment)
  GET  /api/receipt/{txId}    — fetch HCS receipt
  GET  /api/usage             — usage metering
  GET  /api/hashscan/{txId}   — HashScan explorer redirect
  GET  /api/agent/query       — free Hedera Agent Kit demo
  POST /api/agent/query

Interactive docs: http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.middleware.x402 import X402Middleware
from backend.routers import health, demo, payment, receipts, usage, premium, hashscan, agent

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

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── x402 Payment Gate ────────────────────────────────────────────────────────
app.add_middleware(X402Middleware)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health.router,   prefix="/api", tags=["Health"])
app.include_router(demo.router,     prefix="/api", tags=["Demo"])
app.include_router(payment.router,  prefix="/api")
app.include_router(receipts.router, prefix="/api", tags=["Receipts"])
app.include_router(usage.router,    prefix="/api", tags=["Metering"])
app.include_router(premium.router,  prefix="/api", tags=["Premium (Paid)"])
app.include_router(hashscan.router, prefix="/api", tags=["Explorer"])
app.include_router(agent.router,    prefix="/api", tags=["Hedera Agent Kit"])
