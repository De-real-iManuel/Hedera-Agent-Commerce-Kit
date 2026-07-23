"""
hack/metering/service.py
-------------------------
InMemoryMeteringService — a MeteringService backed by a plain list.

Records every successful paid request and provides aggregate statistics.
Suitable for single-process deployments and testing.  For persistent
metering (across restarts or multiple processes), implement the MeteringService
interface with a database or time-series backend.
"""

from __future__ import annotations

from ..core.interfaces import MeteringService
from ..models.quote import UsageRecord, UsageSummary


class InMemoryMeteringService(MeteringService):
    """
    Volatile, in-process metering store.

    Keeps a list of UsageRecord objects and computes a UsageSummary
    on demand by aggregating them.
    """

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    def record(self, usage: UsageRecord) -> None:
        """Append a usage event to the in-memory log."""
        self._records.append(usage)

    def get_summary(self) -> UsageSummary:
        """
        Compute and return aggregate usage statistics.

        total_revenue_hbar is rounded to 8 decimal places to avoid
        floating-point drift across large numbers of records.
        """
        total_requests = len(self._records)
        total_revenue = round(
            sum(r.amount_hbar for r in self._records), 8
        )
        return UsageSummary(
            total_requests=total_requests,
            total_revenue_hbar=total_revenue,
            records=list(self._records),
        )

    def clear(self) -> None:
        """Remove all recorded usage (useful between test cases)."""
        self._records.clear()
