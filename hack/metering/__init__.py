"""
hack/metering/__init__.py
--------------------------
Re-exports the metering service implementation.
"""

from __future__ import annotations

from .service import InMemoryMeteringService

__all__ = ["InMemoryMeteringService"]
