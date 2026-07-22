from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from backend.config import get_settings

router = APIRouter(tags=["explorer"])


@router.get("/hashscan/{tx_id}")
async def hashscan_link(tx_id: str):
    s = get_settings()
    url = f"https://hashscan.io/{s.hedera_network}/transaction/{tx_id}"
    return RedirectResponse(url=url, status_code=302)
