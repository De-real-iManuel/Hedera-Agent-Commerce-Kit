"""
hack/decorator.py
------------------
@PaidEndpoint — the one-line developer API for monetizing any FastAPI route.

Usage:

    from hack import PaidEndpoint

    @app.get("/premium")
    @PaidEndpoint(price="0.5 HBAR", description="Premium AI insight")
    async def premium(request: Request):
        return {"result": "paid access granted"}

The decorator:
  - Resolves the ServiceContainer (lazily from settings if not provided).
  - Reads X-Payment-Token and X-Quote-Id from request headers.
  - Validates that the quote is GRANTED and advances it to CONSUMED.
  - Returns HTTP 402 with structured guidance on all failure paths.

The ``container`` argument allows injection for testing:

    @PaidEndpoint(price="1 HBAR", container=fake_container)
    async def paid_view(request: Request): ...
"""

from __future__ import annotations

import functools
import re
from typing import Any, Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from .core.exceptions import (
    AlreadyConsumedError,
    HACKError,
    PaymentExpiredError,
    QuoteNotFoundError,
)
from .models.quote import PaymentStatus


def _parse_hbar(price: str | float) -> float:
    """Parse '0.5 HBAR', '0.5', or 0.5 → float."""
    if isinstance(price, (int, float)):
        return float(price)
    match = re.match(r"^\s*([\d.]+)\s*(?:HBAR)?\s*$", str(price), re.IGNORECASE)
    if not match:
        raise ValueError(
            f"Cannot parse price {price!r}. Use '0.5 HBAR', '0.5', or a float."
        )
    return float(match.group(1))


class PaidEndpoint:
    """
    Decorator that gates any FastAPI endpoint behind an x402 payment check.

    Args:
        price:       Payment amount.  Accepts '0.5 HBAR', '0.5', or 0.5.
        description: Human-readable description shown in the 402 challenge body.
        container:   Optional pre-built ServiceContainer.  If None, the container
                     is resolved lazily from ServiceContainer.from_settings() on
                     the first request.
    """

    def __init__(
        self,
        price: str | float = "0.5 HBAR",
        description: str = "",
        container: Any = None,
    ) -> None:
        self.amount_hbar = _parse_hbar(price)
        self.description = description
        self._container = container

    def _get_container(self) -> Any:
        """Return injected container or build one lazily from settings."""
        if self._container is None:
            from .container import ServiceContainer
            self._container = ServiceContainer.from_settings()
        return self._container

    def __call__(self, func: Callable) -> Callable:
        amount = self.amount_hbar
        description = self.description or func.__name__
        get_container = self._get_container

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract Request from args or kwargs
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # No Request available — can't gate; let the handler decide.
                return await func(*args, **kwargs)

            container = get_container()
            lifecycle = container.lifecycle
            settings = container.settings

            token = request.headers.get("X-Payment-Token", "").strip()
            quote_id = request.headers.get("X-Quote-Id", "").strip()

            if not token or not quote_id:
                return _payment_required(request, amount, description, settings)

            quote = lifecycle.get_quote(quote_id)
            if quote is None:
                return _payment_required(
                    request, amount, description, settings,
                    detail="Quote not found. Request a new payment challenge.",
                )

            if quote.transaction_id != token:
                return _payment_required(
                    request, amount, description, settings,
                    detail="Payment token does not match quote.",
                )

            if quote.status in (PaymentStatus.EXPIRED,) or (
                __import__("time").time() > quote.expires_at
            ):
                return _payment_required(
                    request, amount, description, settings,
                    detail="Quote expired.",
                )

            if quote.status == PaymentStatus.CONSUMED:
                return _payment_required(
                    request, amount, description, settings,
                    detail="Payment already consumed. Each payment grants one request.",
                )

            if quote.status != PaymentStatus.GRANTED:
                return _payment_required(
                    request, amount, description, settings,
                    detail=(
                        f"Payment not yet granted (status: {quote.status}). "
                        "Verify via POST /api/payment/verify first."
                    ),
                )

            if __import__("time").time() > (quote.grant_expires_at or 0):
                return _payment_required(
                    request, amount, description, settings,
                    detail="Access grant window expired. Verify payment again.",
                )

            try:
                lifecycle.advance_to_consumed(quote_id)
            except (AlreadyConsumedError, PaymentExpiredError, HACKError) as exc:
                return _payment_required(
                    request, amount, description, settings, detail=str(exc)
                )

            return await func(*args, **kwargs)

        wrapper._hack_paid = True  # type: ignore[attr-defined]
        wrapper._hack_amount = amount  # type: ignore[attr-defined]
        wrapper._hack_description = description  # type: ignore[attr-defined]
        return wrapper


def _payment_required(
    request: Request,
    amount_hbar: float,
    description: str,
    settings: Any,
    detail: str = "",
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": "Payment Required",
        "description": description,
        "payment_details": {
            "network": settings.hedera_network,
            "receiver": settings.x402_payment_receiver_account_id,
            "amount_hbar": amount_hbar,
            "memo": settings.x402_payment_memo,
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
            "verify": "POST /api/payment/verify",
            "openapi": "/docs",
        },
    }
    if detail:
        body["detail"] = detail
    return JSONResponse(content=body, status_code=402)
