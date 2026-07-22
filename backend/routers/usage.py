from fastapi import APIRouter
from backend.metering.usage import get_usage

router = APIRouter(tags=["metering"])


@router.get("/usage")
async def usage():
    return get_usage()
