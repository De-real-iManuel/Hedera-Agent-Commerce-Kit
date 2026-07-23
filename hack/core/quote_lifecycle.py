"""
hack/core/quote_lifecycle.py
-----------------------------
QuoteLifecycleService — the authoritative state machine for the x402
payment flow.

Transitions:
  create_quote      →  QUOTED
  advance_to_verified → VERIFIED   (raises on replay, expiry, missing quote)
  advance_to_granted  → GRANTED
  advance_to_consumed → CONSUMED   (raises if already consumed)

The service owns no storage directly; it delegates to an injected QuoteStore.
This makes the business logic fully testable without hitting a database.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Optional

from .exceptions import (
    AlreadyConsumedError,
    PaymentExpiredError,
    QuoteNotFoundError,
    ReplayError,
)
from .interfaces import QuoteStore
from ..models.quote import PaymentStatus, Quote


class QuoteLifecycleService:
    """
    Manages the full lifecycle of a payment quote from issuance to consumption.

    Args:
        store:      A QuoteStore implementation for persistence.
        quote_ttl:  Seconds a QUOTED quote is valid before expiring (default 600).
        grant_ttl:  Seconds a GRANTED quote may be used before expiring (default 300).
    """

    def __init__(
        self,
        store: QuoteStore,
        quote_ttl: int = 600,
        grant_ttl: int = 300,
    ) -> None:
        self._store = store
        self._quote_ttl = quote_ttl
        self._grant_ttl = grant_ttl

    # ─── Public API ───────────────────────────────────────────────────────────

    def create_quote(
        self,
        endpoint: str,
        amount_hbar: float,
        receiver: str,
    ) -> Quote:
        """
        Issue a new payment challenge quote.

        Returns a Quote in QUOTED status with a freshly generated quote_id
        and a resource_hash that binds the quote to this specific endpoint.
        """
        quote_id = str(uuid.uuid4())
        now = time.time()
        resource_hash = hashlib.sha256(
            f"{endpoint}:{quote_id}".encode()
        ).hexdigest()

        quote = Quote(
            quote_id=quote_id,
            endpoint=endpoint,
            amount_hbar=amount_hbar,
            receiver=receiver,
            resource_hash=resource_hash,
            issued_at=now,
            expires_at=now + self._quote_ttl,
            status=PaymentStatus.QUOTED,
        )
        return self._store.create_quote(quote)

    def advance_to_verified(self, quote_id: str, transaction_id: str) -> Quote:
        """
        Advance a QUOTED quote to VERIFIED after Mirror Node confirmation.

        Raises:
            QuoteNotFoundError: quote_id does not exist.
            PaymentExpiredError: the quote TTL has elapsed.
            ReplayError: transaction_id was already used for a different quote.
        """
        quote = self._require_quote(quote_id)
        self._check_not_expired(quote)

        # Replay / duplicate detection via store index
        existing_quotes = self._store.list_quotes()
        for q in existing_quotes:
            if q.transaction_id == transaction_id and q.quote_id != quote_id:
                quote.status = PaymentStatus.DUPLICATE
                self._store.save_quote(quote)
                raise ReplayError(
                    f"Transaction {transaction_id!r} was already applied to "
                    f"quote {q.quote_id!r}. Replay rejected."
                )

        if quote.status == PaymentStatus.VERIFIED:
            # Idempotent re-verification is acceptable
            return quote

        if quote.status != PaymentStatus.QUOTED:
            raise ValueError(
                f"Cannot verify a quote in state {quote.status!r}."
            )

        quote.status = PaymentStatus.VERIFIED
        quote.transaction_id = transaction_id
        return self._store.save_quote(quote)

    def advance_to_granted(self, quote_id: str) -> Quote:
        """
        Advance a VERIFIED quote to GRANTED, opening the access window.

        Raises:
            QuoteNotFoundError: quote_id does not exist.
            PaymentExpiredError: the quote TTL has elapsed.
        """
        quote = self._require_quote(quote_id)
        self._check_not_expired(quote)

        if quote.status == PaymentStatus.GRANTED:
            if time.time() > (quote.grant_expires_at or 0):
                raise PaymentExpiredError("Access grant window has expired.")
            return quote

        if quote.status != PaymentStatus.VERIFIED:
            raise ValueError(
                f"Cannot grant access from state {quote.status!r}."
            )

        now = time.time()
        quote.status = PaymentStatus.GRANTED
        quote.granted_at = now
        quote.grant_expires_at = now + self._grant_ttl
        return self._store.save_quote(quote)

    def advance_to_consumed(self, quote_id: str) -> Quote:
        """
        Advance a GRANTED quote to CONSUMED, marking it as delivered.

        Raises:
            QuoteNotFoundError: quote_id does not exist.
            AlreadyConsumedError: quote was already consumed.
            PaymentExpiredError: grant window elapsed before consumption.
        """
        quote = self._require_quote(quote_id)

        if quote.status == PaymentStatus.CONSUMED:
            raise AlreadyConsumedError(
                f"Quote {quote_id!r} has already been consumed. "
                "Each payment grants exactly one request."
            )

        if quote.status != PaymentStatus.GRANTED:
            raise ValueError(
                f"Cannot consume from state {quote.status!r}."
            )

        if time.time() > (quote.grant_expires_at or 0):
            quote.status = PaymentStatus.EXPIRED
            quote.error = "Grant window expired before result was consumed."
            self._store.save_quote(quote)
            raise PaymentExpiredError(quote.error)

        quote.status = PaymentStatus.CONSUMED
        quote.consumed_at = time.time()
        return self._store.save_quote(quote)

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Return the Quote for the given ID, or None if not found."""
        return self._store.get_quote(quote_id)

    def sweep_expired(self) -> int:
        """
        Mark all QUOTED quotes whose TTL has elapsed as EXPIRED.
        Returns the number of quotes transitioned in this sweep.
        """
        return self._store.sweep_expired()

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _require_quote(self, quote_id: str) -> Quote:
        quote = self._store.get_quote(quote_id)
        if quote is None:
            raise QuoteNotFoundError(f"Quote {quote_id!r} not found.")
        return quote

    def _check_not_expired(self, quote: Quote) -> None:
        if time.time() > quote.expires_at:
            quote.status = PaymentStatus.EXPIRED
            quote.error = (
                f"Quote {quote.quote_id!r} expired at {quote.expires_at}. "
                "Request a new payment challenge."
            )
            self._store.save_quote(quote)
            raise PaymentExpiredError(quote.error)
