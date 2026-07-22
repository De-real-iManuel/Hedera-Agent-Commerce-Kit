"""
x402 Middleware
---------------
Gate: QUOTED → (client pays) → VERIFIED → GRANTED → request proceeds → CONSUMED

Protected routes require both:
  X-Payment-Token: <transaction_id>
  X-Quote-Id:      <quote_id>

A GRANTED quote whose grant window is still open is the only pass condition.
All other states (QUOTED, EXPIRED, DUPLICATE, CONSUMED) return 402 with guidance.
"""

from __future__ import annotations

import time
from typing import Callable, Set

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.config import get_settings
from backend.verification.payment_state import (
    PaymentStatus,
    get_quote,
    advance_to_consumed,
)

PROTECTED_ROUTES: Set[str] = {"/api/premium-query"}


class X402Middleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path not in PROTECTED_ROUTES:
            return await call_next(request)

        token = request.headers.get("X-Payment-Token", "").strip()
        quote_id = request.headers.get("X-Quote-Id", "").strip()

        if not token or not quote_id:
            return self._challenge_response(
                "Payment headers missing.",
                hint="Add 'X-Payment-Token: <tx_id>' and 'X-Quote-Id: <quote_id>' to your request. "
                     "Don't have a quote? POST /api/payment/challenge first.",
            )

        quote = get_quote(quote_id)
        if not quote:
            return self._challenge_response(
                f"Quote '{quote_id}' not found.",
                hint="Quotes expire after 10 minutes. POST /api/payment/challenge to get a fresh one.",
            )

        if quote.transaction_id != token:
            return self._challenge_response(
                "X-Payment-Token does not match this quote.",
                hint="Use the transaction_id returned by /api/payment/verify for this specific quote_id.",
            )

        now = time.time()

        if quote.status == PaymentStatus.EXPIRED or now > quote.expires_at:
            return self._challenge_response(
                "Quote has expired (10-minute TTL).",
                hint="POST /api/payment/challenge to get a new quote, then pay and verify again.",
            )

        if quote.status == PaymentStatus.CONSUMED:
            return self._challenge_response(
                "This payment has already been consumed.",
                hint="Each payment grants exactly one request. POST /api/payment/challenge for a new quote.",
            )

        if quote.status == PaymentStatus.DUPLICATE:
            return self._challenge_response(
                "Duplicate transaction ID detected.",
                hint="This transaction was already applied to a different quote. POST /api/payment/challenge for a new quote.",
                status=409,
            )

        if quote.status != PaymentStatus.GRANTED:
            return self._challenge_response(
                f"Payment not yet verified (status: {quote.status}).",
                hint="POST /api/payment/verify with your {transaction_id, quote_id} to verify the payment first.",
            )

        if now > (quote.grant_expires_at or 0):
            return self._challenge_response(
                "Access grant window has expired (5-minute TTL).",
                hint="POST /api/payment/verify again — this will re-grant access for 5 minutes.",
            )

        # Advance to CONSUMED — only runs the handler once
        try:
            advance_to_consumed(quote_id)
        except ValueError as exc:
            return self._challenge_response(str(exc))

        return await call_next(request)

    @staticmethod
    def _challenge_response(detail: str, hint: str = "", status: int = 402) -> JSONResponse:
        s = get_settings()
        body: dict = {
            "error": "Payment Required" if status == 402 else "Conflict",
            "detail": detail,
        }
        if hint:
            body["hint"] = hint
        body["how_to_pay"] = {
            "step_1": "POST /api/payment/challenge  →  get quote_id + payment details",
            "step_2": "Send HBAR to payment_details.receiver from your Hedera wallet",
            "step_3": "POST /api/payment/verify  {transaction_id, quote_id}  →  get grant",
            "step_4": "Retry with headers:  X-Payment-Token: <tx_id>  X-Quote-Id: <quote_id>",
        }
        body["docs"] = "http://localhost:8000/docs"
        return JSONResponse(content=body, status_code=status)
