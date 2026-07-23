"""
demo/routers/health.py
-----------------------
Health check endpoint — GET /api/health

No payment required.  Returns service status and current configuration
(network only; credentials are never exposed).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request):
    """Return service health and basic configuration metadata."""
    container = request.app.state.container
    s = container.settings
    return {
        "status": "ok",
        "service": "Hedera Agent Commerce Kit",
        "network": s.hedera_network,
        "version": "0.1.0",
    }
