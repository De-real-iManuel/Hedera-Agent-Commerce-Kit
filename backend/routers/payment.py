"""
Payment endpoints
-----------------
POST /api/payment/challenge  — issue a quote + HTTP 402 challenge
POST /api/payment/verify     — verify a Hedera transaction against a quote
                               and advance state: QUOTED → VERIFIED → GRANTED

State transitions are managed by backend.verification.payment_state.
Mirror Node verification lives in backend.verification.mirror_node.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.config import get_settings
from backend.verification.mirror_node import verify_transaction
from backend.verification.payment_state import (
    PaymentStatus,
    create_quote,
    advance_to_verified,
    advance_to_granted,
    get_quote,
)
from backend.receipts.hcs import publish_receipt
from backend.metering.usage import record

router = APIRouter(prefix="/payment", tags=["Payment (x402)"])


class ChallengeRequest(BaseModel):
    endpoint: str = "/api/premium-query"


class VerifyRequest(BaseModel):
    transaction_id: str
    quote_id: str


# ─── POST /api/payment/challenge ─────────────────────────────────────────────

@router.post(
    "/challenge",
    summary="Issue a payment challenge",
    description=(
        "Creates a payment quote and returns an HTTP 402-style challenge. "
        "The client should send the specified HBAR amount to `payment_details.receiver`, "
        "then call `/api/payment/verify` with the resulting transaction ID and this `quote_id`."
    ),
)
async def payment_challenge(body: ChallengeRequest):
    s = get_settings()
    quote = create_quote(
        endpoint=body.endpoint,
        amount_hbar=s.x402_payment_amount_hbar,
        receiver=s.x402_payment_receiver_account_id,
    )
    return {
        "status": 402,
        "quote_id": quote.quote_id,
        "resource_hash": quote.resource_hash,
        "payment_details": {
            "network": s.hedera_network,
            "receiver": quote.receiver,
            "amount_hbar": quote.amount_hbar,
            "memo": s.x402_payment_memo,
            "issued_at": int(quote.issued_at),
            "expires_at": int(quote.expires_at),
        },
        "retry_instructions": (
            "1. Send HBAR to `receiver` with `memo` in the transaction memo field. "
            "2. POST {transaction_id, quote_id} to /api/payment/verify. "
            "3. Retry your original request with header "
            "'X-Payment-Token: <transaction_id>' and 'X-Quote-Id: <quote_id>'."
        ),
    }


# ─── POST /api/payment/verify ────────────────────────────────────────────────

@router.post(
    "/verify",
    summary="Verify a Hedera payment",
    description=(
        "Verifies an HBAR payment against the Hedera Mirror Node. "
        "On success, advances the payment state to GRANTED (5-minute access window). "
        "Publishes an immutable HCS receipt and records usage metering. "
        "**Mirror Node indexing can lag ~3 seconds after consensus — if you receive a 502, retry after a short delay.**"
    ),
)
async def payment_verify(body: VerifyRequest, request: Request):
    tx_id = body.transaction_id.strip()
    quote_id = body.quote_id.strip()
    s = get_settings()

    # 1. Mirror Node — confirm on-chain transfer
    try:
        await verify_transaction(tx_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Mirror Node unavailable: {exc}. Retry after a few seconds.")

    # 2. Advance state machine: QUOTED → VERIFIED → GRANTED
    try:
        advance_to_verified(quote_id, tx_id)
        quote = advance_to_granted(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    caller = request.client.host if request.client else "unknown"

    # 3. Publish HCS receipt
    receipt = await publish_receipt(
        transaction_id=tx_id,
        caller=caller,
        endpoint=quote.endpoint,
        amount_hbar=quote.amount_hbar,
    )

    # 4. Meter usage
    record(
        transaction_id=tx_id,
        caller=caller,
        endpoint=quote.endpoint,
        amount_hbar=quote.amount_hbar,
    )

    return {
        "verified": True,
        "quote_id": quote_id,
        "transaction_id": tx_id,
        "grant_expires_at": int(quote.grant_expires_at or 0),
        "receipt": receipt,
        "next_step": (
            f"Retry your request within {int((quote.grant_expires_at or 0) - time.time())}s "
            f"using headers 'X-Payment-Token: {tx_id}' and 'X-Quote-Id: {quote_id}'."
        ),
    }


# ─── GET /api/payment/status/{quote_id} ──────────────────────────────────────

@router.get("/status/{quote_id}")
async def payment_status(quote_id: str):
    quote = get_quote(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote {quote_id!r} not found.")
    return {
        "quote_id": quote.quote_id,
        "status": quote.status,
        "endpoint": quote.endpoint,
        "amount_hbar": quote.amount_hbar,
        "issued_at": int(quote.issued_at),
        "expires_at": int(quote.expires_at),
        "transaction_id": quote.transaction_id,
        "grant_expires_at": int(quote.grant_expires_at) if quote.grant_expires_at else None,
        "consumed_at": int(quote.consumed_at) if quote.consumed_at else None,
        "error": quote.error,
    }
