"""
Payment State Machine
---------------------
Separates the six stages of a paid request:

  QUOTED → OBSERVED → VERIFIED → GRANTED → CONSUMED → (EXPIRED | REFUNDED)

Binds each payment proof to a specific quote so replayed or mismatched
proofs are rejected. Quotes have explicit TTLs; access grants are bounded.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class PaymentStatus(str, Enum):
    QUOTED = "quoted"          # challenge issued, awaiting payment
    VERIFIED = "verified"      # Mirror Node confirmed correct amount + receiver
    GRANTED = "granted"        # access token issued, not yet consumed
    CONSUMED = "consumed"      # result delivered, meter recorded
    EXPIRED = "expired"        # quote TTL elapsed before payment
    DUPLICATE = "duplicate"    # same tx_id submitted more than once
    REFUNDED = "refunded"      # partial failure — credit/refund owed


QUOTE_TTL_SECONDS: int = 600     # 10 minutes
GRANT_TTL_SECONDS: int = 300     # 5 minutes to use the granted access


@dataclass
class Quote:
    quote_id: str
    endpoint: str
    amount_hbar: float
    receiver: str
    resource_hash: str           # SHA-256 of endpoint + quote_id; binds proof to this quote
    issued_at: float
    expires_at: float
    status: PaymentStatus = PaymentStatus.QUOTED
    transaction_id: Optional[str] = None
    granted_at: Optional[float] = None
    grant_expires_at: Optional[float] = None
    consumed_at: Optional[float] = None
    error: Optional[str] = None


# In-memory store — swap for a DB in production
_quotes: Dict[str, Quote] = {}
_tx_to_quote: Dict[str, str] = {}   # transaction_id → quote_id (duplicate detection)


def create_quote(endpoint: str, amount_hbar: float, receiver: str) -> Quote:
    import hashlib

    quote_id = str(uuid.uuid4())
    now = time.time()
    resource_hash = hashlib.sha256(f"{endpoint}:{quote_id}".encode()).hexdigest()

    quote = Quote(
        quote_id=quote_id,
        endpoint=endpoint,
        amount_hbar=amount_hbar,
        receiver=receiver,
        resource_hash=resource_hash,
        issued_at=now,
        expires_at=now + QUOTE_TTL_SECONDS,
    )
    _quotes[quote_id] = quote
    return quote


def get_quote(quote_id: str) -> Optional[Quote]:
    return _quotes.get(quote_id)


def advance_to_verified(quote_id: str, transaction_id: str) -> Quote:
    """
    Mark a quote as verified after Mirror Node confirmation.
    Raises ValueError for expired quotes, duplicate tx IDs, or unknown quotes.
    """
    quote = _require_quote(quote_id)

    # Replay / duplicate check
    if transaction_id in _tx_to_quote:
        existing = _tx_to_quote[transaction_id]
        if existing != quote_id:
            raise ValueError(
                f"Transaction {transaction_id!r} was already applied to quote {existing!r}. "
                "Replay rejected."
            )

    _check_not_expired(quote)

    if quote.status == PaymentStatus.VERIFIED:
        return quote  # idempotent re-verification is fine

    if quote.status != PaymentStatus.QUOTED:
        raise ValueError(f"Cannot verify quote in state {quote.status!r}.")

    quote.status = PaymentStatus.VERIFIED
    quote.transaction_id = transaction_id
    _tx_to_quote[transaction_id] = quote_id
    return quote


def advance_to_granted(quote_id: str) -> Quote:
    quote = _require_quote(quote_id)
    _check_not_expired(quote)

    if quote.status == PaymentStatus.GRANTED:
        # Idempotent — check grant window still open
        if time.time() > (quote.grant_expires_at or 0):
            raise ValueError("Access grant window has expired.")
        return quote

    if quote.status != PaymentStatus.VERIFIED:
        raise ValueError(f"Cannot grant access from state {quote.status!r}.")

    now = time.time()
    quote.status = PaymentStatus.GRANTED
    quote.granted_at = now
    quote.grant_expires_at = now + GRANT_TTL_SECONDS
    return quote


def advance_to_consumed(quote_id: str) -> Quote:
    quote = _require_quote(quote_id)

    if quote.status == PaymentStatus.CONSUMED:
        return quote  # idempotent result delivery

    if quote.status != PaymentStatus.GRANTED:
        raise ValueError(f"Cannot consume from state {quote.status!r}.")

    if time.time() > (quote.grant_expires_at or 0):
        quote.status = PaymentStatus.EXPIRED
        quote.error = "Grant window expired before result was consumed."
        raise ValueError(quote.error)

    quote.status = PaymentStatus.CONSUMED
    quote.consumed_at = time.time()
    return quote


def expire_stale_quotes() -> int:
    """Sweep expired QUOTED entries. Returns count expired."""
    now = time.time()
    count = 0
    for quote in _quotes.values():
        if quote.status == PaymentStatus.QUOTED and now > quote.expires_at:
            quote.status = PaymentStatus.EXPIRED
            count += 1
    return count


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _require_quote(quote_id: str) -> Quote:
    q = _quotes.get(quote_id)
    if not q:
        raise ValueError(f"Quote {quote_id!r} not found.")
    return q


def _check_not_expired(quote: Quote) -> None:
    if time.time() > quote.expires_at:
        quote.status = PaymentStatus.EXPIRED
        raise ValueError(
            f"Quote {quote.quote_id!r} expired at {quote.expires_at}. "
            "Request a new payment challenge."
        )
