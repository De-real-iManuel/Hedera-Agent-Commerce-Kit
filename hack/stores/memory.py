"""
hack/stores/memory.py
----------------------
InMemoryQuoteStore — a QuoteStore backed by two plain Python dicts.

Suitable for single-process deployments, development, and unit tests.
For multi-process or persistent deployments, replace with a Redis or
database-backed implementation that satisfies the same QuoteStore interface.

Thread safety: the implementation is safe for single-threaded async use
(FastAPI with a single Uvicorn worker).  For multi-threaded scenarios,
wrap mutations in a threading.Lock.
"""

from __future__ import annotations

import time
from typing import Optional

from ..core.interfaces import QuoteStore
from ..models.quote import PaymentStatus, Quote


class InMemoryQuoteStore(QuoteStore):
    """
    Volatile, in-process quote store.

    _quotes maps quote_id → Quote.
    _tx_to_quote maps transaction_id → quote_id for O(1) duplicate detection.
    """

    def __init__(self) -> None:
        self._quotes: dict[str, Quote] = {}
        self._tx_to_quote: dict[str, str] = {}

    # ─── QuoteStore interface ─────────────────────────────────────────────────

    def create_quote(self, quote: Quote) -> Quote:
        """Store a new quote.  Overwrites any existing quote with the same ID."""
        self._quotes[quote.quote_id] = quote
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Return the Quote for the given ID, or None."""
        return self._quotes.get(quote_id)

    def save_quote(self, quote: Quote) -> Quote:
        """Persist an updated quote and update the tx→quote index if needed."""
        self._quotes[quote.quote_id] = quote
        if quote.transaction_id:
            self._tx_to_quote[quote.transaction_id] = quote.quote_id
        return quote

    def list_quotes(self) -> list[Quote]:
        """Return all quotes as a list (order is insertion order in CPython 3.7+)."""
        return list(self._quotes.values())

    def sweep_expired(self) -> int:
        """
        Mark all QUOTED quotes whose TTL has elapsed as EXPIRED.
        Returns the count of newly expired quotes.
        """
        now = time.time()
        count = 0
        for quote in self._quotes.values():
            if quote.status == PaymentStatus.QUOTED and now > quote.expires_at:
                quote.status = PaymentStatus.EXPIRED
                count += 1
        return count

    # ─── Extras (useful for testing) ─────────────────────────────────────────

    def get_quote_by_tx(self, transaction_id: str) -> Optional[Quote]:
        """Return the Quote that has this transaction_id, or None."""
        quote_id = self._tx_to_quote.get(transaction_id)
        if quote_id is None:
            return None
        return self._quotes.get(quote_id)

    def clear(self) -> None:
        """Remove all stored quotes (useful between test cases)."""
        self._quotes.clear()
        self._tx_to_quote.clear()
