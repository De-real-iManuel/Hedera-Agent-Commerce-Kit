"""
hack/audit
-----------
Service-audit engine: probes a developer's live x402/MCP endpoint, fetches
source files from GitHub raw, runs static rule checks, calls an LLM for
recommendations, aggregates everything into a ServiceAuditReport.

Public surface:
    from hack.audit import ServiceAuditor, ReportStore
"""

from __future__ import annotations

from .service_auditor import ServiceAuditor
from .store import ReportStore

__all__ = ["ServiceAuditor", "ReportStore"]
