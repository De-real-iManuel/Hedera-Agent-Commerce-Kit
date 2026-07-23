"""
hack/core/interfaces.py
------------------------
Abstract base classes (ports) that define the contracts between the toolkit
core and concrete infrastructure adapters.

All business logic in the toolkit depends only on these interfaces, making
it trivial to swap in different backends (e.g., Redis QuoteStore, test
doubles) without touching application code.
"""

from __future__ import annotations

import abc
from typing import Optional

from ..models.quote import Quote, ReceiptModel, UsageRecord, UsageSummary


class QuoteStore(abc.ABC):
    """Persistence layer for Quote objects."""

    @abc.abstractmethod
    def create_quote(self, quote: Quote) -> Quote:
        """Persist a newly created quote and return it."""

    @abc.abstractmethod
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Return the Quote for the given ID, or None if not found."""

    @abc.abstractmethod
    def save_quote(self, quote: Quote) -> Quote:
        """Persist an updated quote (after a state transition) and return it."""

    @abc.abstractmethod
    def list_quotes(self) -> list[Quote]:
        """Return all quotes currently held in the store."""

    @abc.abstractmethod
    def sweep_expired(self) -> int:
        """
        Mark all QUOTED quotes whose TTL has elapsed as EXPIRED.
        Returns the number of quotes expired in this sweep.
        """


class PaymentVerifier(abc.ABC):
    """Validates on-chain payment transactions against expected parameters."""

    @abc.abstractmethod
    async def verify(
        self,
        transaction_id: str,
        receiver: str,
        min_tinybars: int,
        network: str,
    ) -> dict:
        """
        Confirm that the given transaction transferred at least *min_tinybars*
        to *receiver* on *network*.

        Returns the raw transaction dict from the Mirror Node on success.
        Raises InsufficientPaymentError, VerifierUnavailableError, or
        ValueError as appropriate.
        """


class ReceiptService(abc.ABC):
    """Stores and optionally publishes payment receipts."""

    @abc.abstractmethod
    async def publish_receipt(self, receipt: ReceiptModel) -> ReceiptModel:
        """
        Persist the receipt and, if configured, publish it to HCS.
        Must never raise — failures are recorded in receipt.hcs_error.
        """

    @abc.abstractmethod
    def get_receipt(self, tx_id: str) -> Optional[ReceiptModel]:
        """Return the cached receipt for the given transaction ID, or None."""


class MeteringService(abc.ABC):
    """Records usage events and produces aggregate summaries."""

    @abc.abstractmethod
    def record(self, usage: UsageRecord) -> None:
        """Persist a single usage event."""

    @abc.abstractmethod
    def get_summary(self) -> UsageSummary:
        """Return aggregate statistics across all recorded usage events."""
