from fastapi import APIRouter

router = APIRouter(tags=["demo"])


@router.get("/demo")
async def demo():
    return {
        "message": "This is a free demo endpoint.",
        "hint": "Hit /api/premium-query to see the x402 payment flow.",
    }
