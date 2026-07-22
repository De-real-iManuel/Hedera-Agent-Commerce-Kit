"""
hack.py — The HACK decorator API
---------------------------------
The single-line developer experience for monetizing any FastAPI endpoint.

Usage:
    from hack import PaidEndpoint

    @app.get("/premium")
    @PaidEndpoint(price="0.5 HBAR", description="Premium AI insight")
    async def premium():
        return {"message": "You unlocked premium access."}

That's it. The decorator:
  - Registers the route in the x402 middleware's protected set
  - Validates payment headers on every request (X-Payment-Token + X-Quote-Id)
  - Advances the payment state machine (GRANTED → CONSUMED)
  - Returns HTTP 402 with a structured challenge when payment is missing

See docs/DECORATOR.md for full usage and examples.
"""

from __future__ import annotations

import functools
import re
import time
from typing import Any, Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.verification.payment_state import (
    PaymentStatus,
    advance_to_consumed,
    get_quote,
)

# Global registry: path → price in HBAR
_paid_routes: dict[str, float] = {}


def _parse_hbar(price: str) -> float:
    """Parse '0.5 HBAR', '0.5', or 0.5 → float."""
    if isinstance(price, (int, float)):
        return float(price)
    match = re.match(r"^\s*([\d.]+)\s*(?:HBAR)?\s*$", str(price), re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot parse price {price!r}. Use '0.5 HBAR' or '0.5'.")
    return float(match.group(1))


class PaidEndpoint:
    """
    Decorator that turns any FastAPI endpoint into a paid x402-gated endpoint.

    Args:
        price:       Required payment amount. Accepts '0.5 HBAR', '0.5', or 0.5.
        description: Optional human-readable description shown in the 402 challenge.

    Example:
        @app.get("/report")
        @PaidEndpoint(price="0.5 HBAR", description="AI-generated report")
        async def report(request: Request):
            return {"data": "..."}
    """

    def __init__(self, price: str | float = "0.5 HBAR", description: str = "") -> None:
        self.amount_hbar = _parse_hbar(price)
        self.description = description

    def __call__(self, func: Callable) -> Callable:
        amount = self.amount_hbar
        description = self.description or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args or kwargs
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # Can't gate without a Request — let the handler decide
                return await func(*args, **kwargs)

            # Register this path in the global paid routes table
            _paid_routes[request.url.path] = amount

            token = request.headers.get("X-Payment-Token", "").strip()
            quote_id = request.headers.get("X-Quote-Id", "").strip()

            if not token or not quote_id:
                return _payment_required(request, amount, description)

            quote = get_quote(quote_id)
            if not quote:
                return _payment_required(
                    request, amount, description,
                    detail="Quote not found. Request a new payment challenge.",
                )

            if quote.transaction_id != token:
                return _payment_required(
                    request, amount, description,
                    detail="Payment token does not match quote.",
                )

            now = time.time()

            if quote.status in (PaymentStatus.EXPIRED,) or now > quote.expires_at:
                return _payment_required(request, amount, description, detail="Quote expired.")

            if quote.status == PaymentStatus.CONSUMED:
                return _payment_required(
                    request, amount, description,
                    detail="Payment already consumed. Each payment grants one request.",
                )

            if quote.status != PaymentStatus.GRANTED:
                return _payment_required(
                    request, amount, description,
                    detail=f"Payment not yet granted (status: {quote.status}). "
                           "Verify via POST /api/payment/verify first.",
                )

            if now > (quote.grant_expires_at or 0):
                return _payment_required(
                    request, amount, description,
                    detail="Access grant window expired. Verify payment again.",
                )

            try:
                advance_to_consumed(quote_id)
            except ValueError as exc:
                return _payment_required(request, amount, description, detail=str(exc))

            return await func(*args, **kwargs)

        # Mark this function as a paid endpoint for introspection
        wrapper._hack_paid = True  # type: ignore[attr-defined]
        wrapper._hack_amount = amount  # type: ignore[attr-defined]
        wrapper._hack_description = description  # type: ignore[attr-defined]
        return wrapper


def _payment_required(
    request: Request,
    amount_hbar: float,
    description: str,
    detail: str = "",
) -> JSONResponse:
    s = get_settings()
    body: dict[str, Any] = {
        "error": "Payment Required",
        "description": description,
        "payment_details": {
            "network": s.hedera_network,
            "receiver": s.x402_payment_receiver_account_id,
            "amount_hbar": amount_hbar,
            "memo": s.x402_payment_memo,
        },
        "how_to_pay": [
            "1. POST /api/payment/challenge to get a quote_id",
            "2. Send HBAR to `receiver` with memo",
            "3. POST /api/payment/verify with {transaction_id, quote_id}",
            "4. Retry this request with headers:",
            "     X-Payment-Token: <transaction_id>",
            "     X-Quote-Id: <quote_id>",
        ],
        "docs": {
            "challenge": "POST /api/payment/challenge",
            "verify":    "POST /api/payment/verify",
            "openapi":   "/docs",
        },
    }
    if detail:
        body["detail"] = detail
    return JSONResponse(content=body, status_code=402)


def get_paid_routes() -> dict[str, float]:
    """Return all routes registered via @PaidEndpoint."""
    return dict(_paid_routes)
