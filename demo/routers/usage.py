"""
demo/routers/usage.py
----------------------
Usage metering endpoint.

GET /api/usage
    Returns aggregate usage statistics and the full record log.

Services are pulled from request.app.state.container.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Metering"])


@router.get(
    "/usage",
    summary="Get usage statistics",
    description="Returns total requests, total revenue in HBAR, and the full usage log.",
)
async def usage(request: Request):
    container = request.app.state.container
    metering = container.metering
    summary = metering.get_summary()
    return summary.model_dump()
