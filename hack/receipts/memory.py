"""
hack/receipts/memory.py
------------------------
InMemoryReceiptService — a ReceiptService backed by a plain dict.

Designed for use in tests and local development where no Hedera credentials
or HCS topic are available.  All receipts are stored in-process and never
published to the network.
"""

from __future__ import annotations

from typing import Optional

from ..core.interfaces import ReceiptService
from ..models.quote import ReceiptModel


class InMemoryReceiptService(ReceiptService):
    """
    Volatile, in-process receipt store.

    publish_receipt() caches the receipt locally and immediately returns
    with hcs_status="published" (simulated) so tests can verify the receipt
    without an actual HCS topic.
    """

    def __init__(self) -> None:
        self._cache: dict[str, ReceiptModel] = {}

    async def publish_receipt(self, receipt: ReceiptModel) -> ReceiptModel:
        """
        'Publish' by storing the receipt in memory.
        Sets hcs_status to "published" to allow tests to assert on the value.
        """
        receipt.hcs_status = "published"
        receipt.hcs_error = None
        self._cache[receipt.transaction_id] = receipt
        return receipt

    def get_receipt(self, tx_id: str) -> Optional[ReceiptModel]:
        """Return the cached receipt for the given transaction ID, or None."""
        return self._cache.get(tx_id)

    def clear(self) -> None:
        """Remove all cached receipts (useful between test cases)."""
        self._cache.clear()
