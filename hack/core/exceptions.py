"""
hack/core/exceptions.py
------------------------
Domain-specific exception hierarchy for the HACK toolkit.

All exceptions derive from HACKError so callers can catch the entire family
with a single `except HACKError` clause, while still being able to handle
individual error conditions precisely.

VerifierUnavailableError is the only retryable exception — it signals a
transient Mirror Node issue rather than a business-logic failure.
"""

from __future__ import annotations


class HACKError(Exception):
    """Base class for all HACK toolkit exceptions."""


class PaymentExpiredError(HACKError):
    """
    Raised when a quote's TTL has elapsed before the payment was verified
    or when a grant window expires before the request is consumed.
    """


class ReplayError(HACKError):
    """
    Raised when a transaction ID is submitted against more than one quote,
    indicating a replay / double-spend attempt.
    """


class InsufficientPaymentError(HACKError):
    """
    Raised by the PaymentVerifier when the transferred amount is less than
    the minimum required by the quote.
    """


class VerifierUnavailableError(HACKError):
    """
    Raised when the Mirror Node returns a 5xx error or is otherwise
    unreachable.  This is a *retryable* condition — the transaction may
    still be valid; the verifier is simply lagging.
    """

    retryable: bool = True


class AlreadyConsumedError(HACKError):
    """
    Raised when an attempt is made to consume a quote that has already
    been consumed, preventing double-delivery of a paid result.
    """


class QuoteNotFoundError(HACKError):
    """
    Raised when a quote_id is referenced but does not exist in the store.
    """
