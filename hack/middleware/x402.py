"""
hack/middleware/x402.py
------------------------
X402Middleware — Starlette BaseHTTPMiddleware that gates a configurable set
of routes behind the x402 payment flow.

The middleware:
  1. Passes non-protected routes through immediately.
  2. Reads X-Payment-Token and X-Quote-Id headers.
  3. Validates the quote against the lifecycle service.
  4. Advances the quote from GRANTED → CONSUMED exactly once.
  5. Returns a structured 402 JSON body for every failure case.

The lifecycle service is fully injected — no global state is used.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.exceptions import (
    AlreadyConsumedError,
    HACKError,
    PaymentExpiredError,
    QuoteNotFoundError,
)
from ..core.quote_lifecycle import QuoteLifecycleService
from ..models.quote import PaymentStatus


class X402Middleware(BaseHTTPMiddleware):
    """
    HTTP 402 payment gate middleware.

    Args:
        app:               The ASGI application to wrap.
        lifecycle:         Injected QuoteLifecycleService.
        protected_routes:  Set of exact path strings that require payment.
                           Defaults to {"/api/premium-query"}.
    """

    def __init__(
        self,
        app: ASGIApp,
        lifecycle: QuoteLifecycleService,
        protected_routes: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._lifecycle = lifecycle
        self._protected = protected_routes or {"/api/premium-query"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path not in self._protected:
            return await call_next(request)

        token = request.headers.get("X-Payment-Token", "").strip()
        quote_id = request.headers.get("X-Quote-Id", "").strip()

        if not token or not quote_id:
            return self._challenge_response(
                "Payment headers missing.",
                hint=(
                    "Add 'X-Payment-Token: <tx_id>' and 'X-Quote-Id: <quote_id>' "
                    "to your request. Don't have a quote? POST /api/payment/challenge first."
                ),
            )

        quote = self._lifecycle.get_quote(quote_id)
        if quote is None:
            return self._challenge_response(
                f"Quote '{quote_id}' not found.",
                hint="Quotes expire after 10 minutes. POST /api/payment/challenge to get a fresh one.",
            )

        if quote.transaction_id != token:
            return self._challenge_response(
                "X-Payment-Token does not match this quote.",
                hint=(
                    "Use the transaction_id returned by /api/payment/verify "
                    "for this specific quote_id."
                ),
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
                hint=(
                    "Each payment grants exactly one request. "
                    "POST /api/payment/challenge for a new quote."
                ),
            )

        if quote.status == PaymentStatus.DUPLICATE:
            return self._challenge_response(
                "Duplicate transaction ID detected.",
                hint=(
                    "This transaction was already applied to a different quote. "
                    "POST /api/payment/challenge for a new quote."
                ),
                status=409,
            )

        if quote.status != PaymentStatus.GRANTED:
            return self._challenge_response(
                f"Payment not yet verified (status: {quote.status}).",
                hint=(
                    "POST /api/payment/verify with your {transaction_id, quote_id} "
                    "to verify the payment first."
                ),
            )

        if now > (quote.grant_expires_at or 0):
            return self._challenge_response(
                "Access grant window has expired (5-minute TTL).",
                hint="POST /api/payment/verify again to renew the access grant.",
            )

        try:
            self._lifecycle.advance_to_consumed(quote_id)
        except AlreadyConsumedError as exc:
            return self._challenge_response(str(exc))
        except PaymentExpiredError as exc:
            return self._challenge_response(str(exc))
        except HACKError as exc:
            return self._challenge_response(str(exc))

        return await call_next(request)

    @staticmethod
    def _challenge_response(
        detail: str,
        hint: str = "",
        status: int = 402,
    ) -> JSONResponse:
        body: dict = {
            "error": "Payment Required" if status == 402 else "Conflict",
            "detail": detail,
        }
        if hint:
            body["hint"] = hint
        body["how_to_pay"] = [
            "1. POST /api/payment/challenge  →  receive quote_id + payment details",
            "2. Send HBAR to payment_details.receiver from your Hedera wallet",
            "3. POST /api/payment/verify  {transaction_id, quote_id}  →  receive grant",
            "4. Retry with headers:  X-Payment-Token: <tx_id>  X-Quote-Id: <quote_id>",
        ]
        body["docs"] = "/docs"
        return JSONResponse(content=body, status_code=status)
