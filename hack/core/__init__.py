"""
hack/core/__init__.py
----------------------
Re-exports the public core API: interfaces, exceptions, and the lifecycle service.
"""

from __future__ import annotations

from .exceptions import (
    AlreadyConsumedError,
    HACKError,
    InsufficientPaymentError,
    PaymentExpiredError,
    QuoteNotFoundError,
    ReplayError,
    VerifierUnavailableError,
)
from .interfaces import MeteringService, PaymentVerifier, QuoteStore, ReceiptService
from .quote_lifecycle import QuoteLifecycleService

__all__ = [
    "QuoteStore",
    "PaymentVerifier",
    "ReceiptService",
    "MeteringService",
    "QuoteLifecycleService",
    "HACKError",
    "PaymentExpiredError",
    "ReplayError",
    "InsufficientPaymentError",
    "VerifierUnavailableError",
    "AlreadyConsumedError",
    "QuoteNotFoundError",
]
