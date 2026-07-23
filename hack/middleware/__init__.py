"""
hack/middleware/__init__.py
----------------------------
Re-exports the x402 payment gate middleware.
"""

from __future__ import annotations

from .x402 import X402Middleware

__all__ = ["X402Middleware"]
