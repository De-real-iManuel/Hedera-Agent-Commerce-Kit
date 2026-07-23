"""
hack/receipts/__init__.py
--------------------------
Re-exports concrete ReceiptService implementations.
"""

from __future__ import annotations

from .hcs import HCSReceiptService
from .memory import InMemoryReceiptService

__all__ = ["HCSReceiptService", "InMemoryReceiptService"]
