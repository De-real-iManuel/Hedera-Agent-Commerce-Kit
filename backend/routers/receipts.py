from fastapi import APIRouter, HTTPException
from backend.receipts.hcs import get_receipt

router = APIRouter(tags=["receipts"])


@router.get("/receipt/{tx_id}")
async def fetch_receipt(tx_id: str):
    receipt = get_receipt(tx_id)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Receipt for '{tx_id}' not found.")
    return receipt
