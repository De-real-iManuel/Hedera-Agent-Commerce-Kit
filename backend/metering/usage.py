"""
Usage Metering
--------------
Records every successful paid request in memory.
Exposes aggregate stats for the /api/usage endpoint.
"""

from __future__ import annotations

import time
from typing import List, Dict, Any

_records: List[Dict[str, Any]] = []


def record(*, transaction_id: str, caller: str, endpoint: str, amount_hbar: float) -> None:
    _records.append(
        {
            "transaction_id": transaction_id,
            "caller": caller,
            "endpoint": endpoint,
            "amount_hbar": amount_hbar,
            "timestamp": int(time.time()),
        }
    )


def get_usage() -> Dict[str, Any]:
    total_requests = len(_records)
    total_revenue = sum(r["amount_hbar"] for r in _records)
    return {
        "total_requests": total_requests,
        "total_revenue_hbar": round(total_revenue, 8),
        "records": _records,
    }
