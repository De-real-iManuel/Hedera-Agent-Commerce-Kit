"""
demo/routers/payment.py
------------------------
Payment lifecycle endpoints.

POST /api/payment/challenge    — issue a quote + HTTP 402 challenge
POST /api/payment/verify       — verify payment on Mirror Node; advance to GRANTED
GET  /api/payment/status/{id}  — inspect current quote state

All services are pulled from request.app.state.container — no module-level
globals are used here.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hack.models.quote import ReceiptModel, UsageRecord

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
        "Send the specified HBAR amount to `payment_details.receiver`, "
        "then call `/api/payment/verify` with the transaction ID and `quote_id`."
    ),
)
async def payment_challenge(body: ChallengeRequest, request: Request):
    container = request.app.state.container
    s = container.settings
    lifecycle = container.lifecycle

    quote = lifecycle.create_quote(
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
            "3. Retry your original request with headers "
            "'X-Payment-Token: <transaction_id>' and 'X-Quote-Id: <quote_id>'."
        ),
    }


# ─── POST /api/payment/verify ────────────────────────────────────────────────

@router.post(
    "/verify",
    summary="Verify a Hedera payment",
    description=(
        "Verifies an HBAR payment on the Mirror Node and advances the quote "
        "to GRANTED (5-minute access window).  "
        "**Mirror Node indexing can lag ~3 seconds — if you get a 502, retry shortly.**"
    ),
)
async def payment_verify(body: VerifyRequest, request: Request):
    container = request.app.state.container
    s = container.settings
    lifecycle = container.lifecycle
    verifier = container.verifier
    receipt_service = container.receipt_service
    metering = container.metering

    tx_id = body.transaction_id.strip()
    quote_id = body.quote_id.strip()

    # 1. Confirm on-chain transfer via Mirror Node
    try:
        min_tinybars = int(s.x402_payment_amount_hbar * 100_000_000)
        await verifier.verify(
            transaction_id=tx_id,
            receiver=s.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=s.hedera_network,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Mirror Node unavailable: {exc}. Retry after a few seconds.",
        )

    # 2. Advance state machine: QUOTED → VERIFIED → GRANTED
    from hack.core.exceptions import HACKError
    try:
        lifecycle.advance_to_verified(quote_id, tx_id)
        quote = lifecycle.advance_to_granted(quote_id)
    except HACKError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    caller = request.client.host if request.client else "unknown"

    # 3. Publish HCS receipt
    receipt = ReceiptModel(
        transaction_id=tx_id,
        caller=caller,
        endpoint=quote.endpoint,
        amount_hbar=quote.amount_hbar,
        timestamp=int(time.time()),
        hashscan_url=(
            f"https://hashscan.io/{s.hedera_network}/transaction/{tx_id}"
        ),
    )
    published_receipt = await receipt_service.publish_receipt(receipt)

    # 4. Record usage
    metering.record(
        UsageRecord(
            transaction_id=tx_id,
            caller=caller,
            endpoint=quote.endpoint,
            amount_hbar=quote.amount_hbar,
            timestamp=int(time.time()),
        )
    )

    remaining = int((quote.grant_expires_at or 0) - time.time())
    return {
        "verified": True,
        "quote_id": quote_id,
        "transaction_id": tx_id,
        "grant_expires_at": int(quote.grant_expires_at or 0),
        "receipt": published_receipt.model_dump(),
        "next_step": (
            f"Retry your request within {max(remaining, 0)}s using headers "
            f"'X-Payment-Token: {tx_id}' and 'X-Quote-Id: {quote_id}'."
        ),
    }


# ─── GET /api/payment/status/{quote_id} ──────────────────────────────────────

@router.get(
    "/status/{quote_id}",
    summary="Get quote status",
)
async def payment_status(quote_id: str, request: Request):
    container = request.app.state.container
    lifecycle = container.lifecycle

    quote = lifecycle.get_quote(quote_id)
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
