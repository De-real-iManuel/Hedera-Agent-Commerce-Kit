"""
hack/stores/__init__.py
------------------------
Re-exports concrete QuoteStore implementations.
"""

from __future__ import annotations

from .memory import InMemoryQuoteStore

__all__ = ["InMemoryQuoteStore"]
