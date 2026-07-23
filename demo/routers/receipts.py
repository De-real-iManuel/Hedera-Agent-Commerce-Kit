"""
demo/routers/receipts.py
-------------------------
Receipt retrieval endpoint.

GET /api/receipt/{tx_id}
    Returns the cached receipt for the given transaction ID.

Services are pulled from request.app.state.container.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["Receipts"])


@router.get(
    "/receipt/{tx_id}",
    summary="Fetch a payment receipt",
    description="Returns the HCS receipt published during payment verification.",
)
async def fetch_receipt(tx_id: str, request: Request):
    container = request.app.state.container
    receipt_service = container.receipt_service

    receipt = receipt_service.get_receipt(tx_id)
    if receipt is None:
        raise HTTPException(
            status_code=404,
            detail=f"Receipt for transaction '{tx_id}' not found.",
        )
    return receipt.model_dump()
