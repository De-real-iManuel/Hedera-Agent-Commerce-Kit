"""
demo/routers/hashscan.py
-------------------------
HashScan explorer redirect.

GET /api/hashscan/{tx_id}
    Redirects to the HashScan explorer page for the given transaction.

Services are pulled from request.app.state.container.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Explorer"])


@router.get(
    "/hashscan/{tx_id}",
    summary="Redirect to HashScan",
    description="Redirects the caller to the HashScan explorer for the transaction.",
)
async def hashscan_link(tx_id: str, request: Request):
    container = request.app.state.container
    s = container.settings
    url = f"https://hashscan.io/{s.hedera_network}/transaction/{tx_id}"
    return RedirectResponse(url=url, status_code=302)
